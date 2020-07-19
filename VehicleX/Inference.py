import numpy as np
import random
from skimage import io
from skimage import img_as_ubyte
import argparse
import os
import sys
from xml.dom.minidom import Document
import json
from mlagents.envs.environment import UnityEnvironment

parser = argparse.ArgumentParser(description='outputs')
parser.add_argument('--setting',default='./VehicleID-out.json',type=str, help='./target dataset and attribute definition')
parser.add_argument('--train_mode',default=False, help='Whether to run the environment in training or inference mode')
parser.add_argument('--env_path', type=str, default='./Build-win/Unity Environment')
parser.add_argument('--out_lab_file', type=str, default='train_label.xml')

opt = parser.parse_args()
env_name = opt.env_path # is ./Build-linux/VehicleX if linux is used
train_mode = opt.train_mode  # Whether to run the environment in training or inference mode

print("Python version:")
print(sys.version)

# check Python version
if (sys.version_info[0] < 3):
    raise Exception("ERROR: ML-Agents Toolkit (v0.3 onwards) requires Python 3")

# env = UnityEnvironment(file_name=env_name)
env = UnityEnvironment(file_name=env_name) # is None if you use Unity Editor
# Set the default brain to work with

default_brain = env.brain_names[0]
brain = env.brains[default_brain]
distance_bias = 12.11

def ancestral_sampler_1(pi=[0.5, 0.5], 
                      mu=[0, 180], sigma=[20, 20], size=1):
    sigma = [20 for i in range(6)]
    pi = [0.16 for i in range(6)]
    sample = []
    z_list = np.random.uniform(size=size)    
    low = 0 # low bound of a pi interval
    high = 0 # higg bound of a pi interval
    for index in range(len(pi)):
        if index >0:
            low += pi[index - 1]
        high += pi[index]
        s = len([z for z in z_list if low <= z < high])
        sample.extend(np.random.normal(loc=mu[index], scale=np.sqrt(sigma[index]), size=s))
    return sample

print ("Begin generation")

doc = Document()
TrainingImages = doc.createElement('TrainingImages')
TrainingImages.setAttribute("Version", "1.0")  
doc.appendChild(TrainingImages)
Items = doc.createElement('Items')
Items.setAttribute("number", "-")  
TrainingImages.appendChild(Items)

def Get_Save_images_by_attributes(attribute_list, cam_id, dataset_size, output_dir):
    if not os.path.isdir(output_dir):  
        os.mkdir(output_dir)
    z = 0
    cnt = 0
    angle = np.random.permutation (ancestral_sampler_1(pi = [], mu = attribute_list[:6], size=dataset_size * 3))
    temp_intensity_list = np.random.normal(loc=attribute_list[6], scale=np.sqrt(0.4), size=dataset_size * 3)  
    temp_light_direction_x_list = np.random.normal(loc=attribute_list[7], scale=np.sqrt(50), size=dataset_size * 3)
    Cam_height_list = np.random.normal(loc=attribute_list[8], scale=2, size=dataset_size * 3) 
    Cam_distance_y_list = np.random.normal(loc=attribute_list[9], scale=3, size=dataset_size * 3) 
    cam_str = "c" + str(cam_id).zfill(3)
    env_info = env.reset(train_mode=train_mode)[default_brain]
    images = []
    while cnt < dataset_size:
        done = False
        if angle[z] > 360:
            angle[z] = angle[z] % 360
        while angle[z] < 0:
            angle[z] =  angle[z] + 360
        Cam_distance_x = random.uniform(-5, 5)
        scene_id = random.randint(1,59) 
        env_info = env.step([[angle[z], temp_intensity_list[z], temp_light_direction_x_list[z], Cam_distance_y_list[z], Cam_distance_x, Cam_height_list[z], scene_id, train_mode]])[default_brain] 
        done = env_info.local_done[0]
        car_id = int(env_info.vector_observations[0][4])
        color_id = int(env_info.vector_observations[0][5])
        type_id = int(env_info.vector_observations[0][6])
        if done:
            env_info = env.reset(True)[default_brain]
            continue
        observation_gray = np.array(env_info.visual_observations[1])
        x, y = (observation_gray[0,:,:,0] > 0).nonzero()
        observation = np.array(env_info.visual_observations[0])
        if observation.shape[3] == 3 and len(y) > 0 and min(y) > 10 and min(x) > 10:
            print (cam_id, cnt, angle[z], temp_intensity_list[z], temp_light_direction_x_list[z], Cam_distance_y_list[z], Cam_distance_x, Cam_height_list[z], scene_id)
            ori_img = observation[0,min(x)-10:max(x)+10,min(y)-10:max(y)+10,:]
            cnt = cnt + 1
            filename = "0" + str(car_id).zfill(4) + "_" + cam_str + "_" + str(cnt) + ".jpg"
            io.imsave(output_dir + filename,img_as_ubyte(ori_img))
            Item = doc.createElement('Item')
            Item.setAttribute("typeID", str(type_id))  
            Item.setAttribute("imageName", filename)   
            Item.setAttribute("cameraID", cam_str)  
            Item.setAttribute("vehicleID", str(car_id).zfill(4))  
            Item.setAttribute("colorID", str(color_id))  
            Item.setAttribute("orientation",str(round(angle[z], 1)))
            Item.setAttribute("lightInt",str(round(temp_intensity_list[z], 1)))
            Item.setAttribute("lightDir",str(round(temp_light_direction_x_list[z], 1)))
            Item.setAttribute("camHei",str(round(Cam_height_list[z], 1)))
            Item.setAttribute("camDis",str(round(Cam_distance_y_list[z] + distance_bias, 1)))
            Items.appendChild(Item)
        z = z + 1

def get_cam_attr(cam_info):
    control_list = []
    attribute_list = []
    variance_list = []
    for attribute in cam_info['attributes'].items():
        attribute_name = attribute[0]
        attribute_content = attribute[1]
        if attribute_content[0] == 'Gaussian Mixture':
            range_info = attribute_content[1]
            mean_list = attribute_content[2]
            var_list = attribute_content[3]
            control_list.extend([np.arange(range_info[0], range_info[1], range_info[2]) for i in range (len(mean_list))])
            attribute_list.extend(mean_list)
            variance_list.extend(var_list)
        if attribute_content[0] == 'Gaussian':
            range_info = attribute_content[1]
            mean_list = attribute_content[2]
            var_list = attribute_content[3]
            control_list.append (np.arange(range_info[0], range_info[1], range_info[2]))
            attribute_list.append (mean_list)
            variance_list.append (var_list)
    return control_list, attribute_list, variance_list

with open(opt.setting) as f:
    task_info = json.load(f)

for cam_id in range(task_info['camera number']):
    cam_info = task_info['camera list'][cam_id]
    control_list, attribute_list, variance_list = get_cam_attr(cam_info)
    Get_Save_images_by_attributes(attribute_list, cam_id, cam_info['data size'], cam_info['output dir'])

with open(opt.out_lab_file, 'wb') as f:
    f.write(doc.toprettyxml(indent='\t', newl = "\n", encoding='utf-8'))
f.close()  
