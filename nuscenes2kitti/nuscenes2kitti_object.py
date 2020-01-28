''' Helper class and functions for loading nuscenes2kitti objects
'''
from __future__ import print_function

import os
import sys
import numpy as np
import cv2
from PIL import Image
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
sys.path.append(os.path.join(ROOT_DIR, 'mayavi'))
import nuscenes2kitti_util as utils
import ipdb
from pyquaternion import Quaternion
try:
    raw_input          # Python 2
except NameError:
    raw_input = input  # Python 3


class nuscenes2kitti_object(object):
    '''Load and parse object data into a usable format.'''
    
    def __init__(self, root_dir, split='v1.0-mini'):
        '''root_dir contains training and testing folders'''
        self.root_dir = root_dir
        self.split = split
        self.split_dir = os.path.join(root_dir, split)

        if split == 'v1.0-mini':
            self.num_samples = 404
        elif split == 'v1.0-training':
            self.num_samples = 10000
        elif split == 'v1.0-test':
            self.num_samples = 10000
        else:
            print('Unknown split: %s' % (split))
            exit(-1)

        self.CAM_FRONT_dir = os.path.join(self.split_dir, 'image_CAM_FRONT')
        self.CAM_FRONT_RIGHT_dir = os.path.join(self.split_dir, 'image_CAM_FRONT_RIGHT')
        self.CAM_BACK_RIGHT_dir = os.path.join(self.split_dir, 'image_CAM_BACK_RIGHT')
        self.CAM_BACK_dir = os.path.join(self.split_dir, 'image_CAM_BACK')
        self.CAM_BACK_LEFT_dir = os.path.join(self.split_dir, 'image_CAM_BACK_LEFT')
        self.CAM_FRONT_LEFT_dir = os.path.join(self.split_dir, 'image_CAM_FRONT_LEFT')

        self.calib_dir = os.path.join(self.split_dir, 'calib')
        self.lidar_dir = os.path.join(self.split_dir, 'LIDAR_TOP')

        self.label_CAM_FRONT_dir = os.path.join(self.split_dir, 'label_CAM_FRONT')
        self.label_CAM_FRONT_RIGHT_dir = os.path.join(self.split_dir, 'label_CAM_FRONT_RIGHT')
        self.label_CAM_BACK_RIGHT_dir = os.path.join(self.split_dir, 'label_CAM_BACK_RIGHT')
        self.label_CAM_BACK_dir = os.path.join(self.split_dir, 'label_CAM_BACK')
        self.label_CAM_BACK_LEFT_dir = os.path.join(self.split_dir, 'label_CAM_BACK_LEFT')
        self.label_CAM_FRONT_LEFT_dir = os.path.join(self.split_dir, 'label_CAM_FRONT_LEFT')

    def __len__(self):
        return self.num_samples

    def get_image(self, sensor, idx):
        assert(idx<self.num_samples)
        assert (sensor in ['CAM_FRONT', 'CAM_BACK', 'CAM_FRONT_LEFT', 'CAM_BACK_LEFT', 'CAM_FRONT_RIGHT',
                           'CAM_BACK_RIGHT'])
        img_filename = os.path.join(getattr(self,sensor+'_dir'), '%06d.jpg'%(idx))
        return utils.load_image(img_filename)

    def get_lidar(self, idx): 
        assert(idx<self.num_samples) 
        lidar_filename = os.path.join(self.lidar_dir, '%06d.bin'%(idx))
        return utils.load_velo_scan(lidar_filename)

    def get_calibration(self, idx):
        assert(idx<self.num_samples)
        calib_filename = os.path.join(self.calib_dir, '%06d.txt'%(idx))
        return utils.Calibration(calib_filename)

    def get_label_objects(self, sensor, idx):
        assert(idx<self.num_samples and self.split!='v1.0-test')
        assert (sensor in ['CAM_FRONT', 'CAM_BACK', 'CAM_FRONT_LEFT', 'CAM_BACK_LEFT', 'CAM_FRONT_RIGHT',
                           'CAM_BACK_RIGHT'])
        label_filename = os.path.join(getattr(self,'label_'+sensor+'_dir'), '%06d.txt'%(idx))
        return utils.read_label(label_filename)
        
    def get_depth_map(self, idx):
        pass

    def get_top_down(self, idx):
        pass
def render_objects(img, objects, view=np.eye(4), colors = ((0, 0, 255), (255, 0, 0), (155, 155, 155)),linewidth=2):
    def draw_rect(selected_corners, color):
        prev = selected_corners[-1]
        for corner in selected_corners:
            cv2.line(img,
                     (int(prev[0]), int(prev[1])),
                     (int(corner[0]), int(corner[1])),
                     color, linewidth=linewidth)
            prev = corner

    for obj in objects:
        if obj.type=='DontCare':continue
        box3d_pts_2d, box3d_pts_3d = utils.compute_box_3d(obj, view)

        # Draw the sides
        for i in range(4):
            cv2.line(img,
                     (int(corners_2d.T[i][0]), int(corners_2d.T[i][1])),
                     (int(corners_2d.T[i + 4][0]), int(corners_2d.T[i + 4][1])),
                     colors[c][::-1], linewidth)

        # Draw front (first 4 corners) and rear (last 4 corners) rectangles(3d)/lines(2d)
        draw_rect(corners_2d.T[:4], colors[c][::-1])
        draw_rect(corners_2d.T[4:], colors[c][::-1])

        corners_2d = box3d_pts_2d

        # Draw line indicating the front
        center_bottom_forward = np.mean(corners_2d.T[0:2], axis=0)
        center_bottom = np.mean(corners_2d.T[[0, 1, 2, 3]], axis=0)
        # center_bottom_forward = np.mean(corners_2d.T[2:4], axis=0)
        # center_bottom = np.mean(corners_2d.T[[2, 3, 7, 6]], axis=0)
        cv2.line(img,
                 (int(center_bottom[0]), int(center_bottom[1])),
                 (int(center_bottom_forward[0]), int(center_bottom_forward[1])),
                 colors[0][::-1], linewidth)

def show_image_with_boxes(img, objects, view, show3d=True,linewidth=2,colors = ((0, 0, 255), (255, 0, 0), (155, 155, 155))):
    ''' Show image with 2D bounding boxes '''
    img1 = np.copy(img) # for 2d bbox
    img2 = np.copy(img) # for 3d bbox
    type2color = {'Pedestrian':0,
                  'Car':1,
                  'Cyclist':2}
    for obj in objects:
        if obj.type=='DontCare':continue
        if obj.type not in type2color.keys():continue
        c = type2color[obj.type]
        cv2.rectangle(img1, (int(obj.xmin),int(obj.ymin)),
            (int(obj.xmax),int(obj.ymax)), colors[c][::-1], 2)

        box3d_pts_2d, box3d_pts_3d = utils.compute_box_3d(obj, view)

        #img2 = utils.draw_projected_box3d(img2, box3d_pts_2d)
        def draw_rect(selected_corners, color):
            prev = selected_corners[-1]
            for corner in selected_corners:
                cv2.line(img2,
                         (int(prev[0]), int(prev[1])),
                         (int(corner[0]), int(corner[1])),
                         color, linewidth)
                prev = corner

        corners_2d = box3d_pts_2d
        # Draw the sides
        for i in range(4):
            cv2.line(img2,
                     (int(corners_2d.T[i][0]), int(corners_2d.T[i][1])),
                     (int(corners_2d.T[i + 4][0]), int(corners_2d.T[i + 4][1])),
                     colors[c][::-1], linewidth)

        # Draw front (first 4 corners) and rear (last 4 corners) rectangles(3d)/lines(2d)
        draw_rect(corners_2d.T[:4], colors[c][::-1])
        draw_rect(corners_2d.T[4:], colors[c][::-1])

        # Draw line indicating the front
        center_bottom_forward = np.mean(corners_2d.T[0:2], axis=0)
        center_bottom = np.mean(corners_2d.T[[0, 1, 2, 3]], axis=0)
        # center_bottom_forward = np.mean(corners_2d.T[2:4], axis=0)
        # center_bottom = np.mean(corners_2d.T[[2, 3, 7, 6]], axis=0)
        cv2.line(img2,
                 (int(center_bottom[0]), int(center_bottom[1])),
                 (int(center_bottom_forward[0]), int(center_bottom_forward[1])),
                 colors[c][::-1], linewidth)

    Image.fromarray(img1).show()
    if show3d:
        Image.fromarray(img2).show()

def project_velo_to_image(calib, view, pts_3d_velo):
    ''' Input: nx3 points in velodyne coord.
        Output: nx2 points in image2 coord.
    '''
    # Points live in the point sensor frame. So they need to be transformed via global to the image plane.
    # First step: transform the point-cloud to the ego vehicle frame for the timestamp of the sweep.
    pts_3d_ego = rotate(pts_3d_velo, getattr(calib,'lidar2ego_rotation'))
    pts_3d_ego = translate(pts_3d_ego, getattr(calib,'lidar2ego_translation'))

    # Second step: transform to the global frame.
    pts_3d_global=rotate(pts_3d_egp,getattr(calib,'ego2global_rotation'))
    pts_3d_global=translate(pts_3d_global,getattr(calib,'ego2global_translation'))

    # Third step: transform into the ego vehicle frame for the timestamp of the image.
    poserecord = self.nusc.get('ego_pose', cam['ego_pose_token'])
    pc.translate(-np.array(poserecord['translation']))
    pc.rotate(Quaternion(poserecord['rotation']).rotation_matrix.T)

    # Fourth step: transform into the camera.
    cs_record = self.nusc.get('calibrated_sensor', cam['calibrated_sensor_token'])
    pc.translate(-np.array(cs_record['translation']))
    pc.rotate(Quaternion(cs_record['rotation']).rotation_matrix.T)
    return utils.view_points(pts_3d_velo[:, :3].T, view, normalize=False).T

def get_lidar_in_image_fov(pc_velo, calib, view, xmin, ymin, xmax, ymax,
                           return_more=False, clip_distance=2.0):
    ''' Filter lidar points, keep those in image FOV '''
    '''    imgfov_pc_velo, pts_2d, fov_inds = get_lidar_in_image_fov(pc_velo,
        view, 0, 0, img_width, img_height, True)'''
    pts_2d = project_velo_to_image(calib, view, pc_velo)
    fov_inds = (pts_2d[:,0]<xmax) & (pts_2d[:,0]>=xmin) & \
        (pts_2d[:,1]<ymax) & (pts_2d[:,1]>=ymin)
    fov_inds = fov_inds & (pc_velo[:,0]>clip_distance)
    imgfov_pc_velo = pc_velo[fov_inds,:]
    if return_more:
        return imgfov_pc_velo, pts_2d, fov_inds
    else:
        return imgfov_pc_velo
"""
def draw_lidar_simple(pc, color=None):
    ''' Draw lidar points. simplest set up. '''
    import mayavi.mlab as mlab
    fig = mlab.figure(figure=None, bgcolor=(0,0,0), fgcolor=None, engine=None, size=(1600, 1000))
    if color is None: color = pc[:,2]
    #draw points
    mlab.points3d(pc[:,0], pc[:,2], pc[:,1], color, color=None, mode='point', colormap = 'gnuplot', scale_factor=1, figure=fig)
    #draw origin
    mlab.points3d(0, 0, 0, color=(1,1,1), mode='sphere', scale_factor=0.2)
    #draw axis
    axes=np.array([
        [2.,0.,0.,0.],
        [0.,0.,2.,0.],
        [0.,2.,0.,0.],
    ],dtype=np.float64)
    mlab.plot3d([0, axes[0,0]], [0, axes[0,1]], [0, axes[0,2]], color=(1,0,0), tube_radius=None, figure=fig)
    mlab.plot3d([0, axes[1,0]], [0, axes[1,1]], [0, axes[1,2]], color=(0,1,0), tube_radius=None, figure=fig)
    mlab.plot3d([0, axes[2,0]], [0, axes[2,1]], [0, axes[2,2]], color=(0,0,1), tube_radius=None, figure=fig)
    mlab.view(azimuth=180, elevation=70, focalpoint=[ 12.0909996 , -1.04700089, -2.03249991], distance=62.0, figure=fig)
    return fig
"""
def show_lidar_with_boxes(pc_velo, objects, calib, view,
                          img_fov=False, img_width=None, img_height=None): 
    ''' Show all LiDAR points.
        Draw 3d box in LiDAR point cloud (in velo coord system) '''
    if 'mlab' not in sys.modules: import mayavi.mlab as mlab
    from viz_util import draw_lidar_simple
    from viz_util import draw_lidar
    from viz_util import draw_gt_boxes3d

    print(('All point num: ', pc_velo.shape[0]))
    #fig = mlab.figure(figure=None, bgcolor=(0,0,0),
    #    fgcolor=None, engine=None, size=(1000, 500))
    if img_fov:
        pc_velo = get_lidar_in_image_fov(pc_velo, view, 0, 0,
            img_width, img_height)
        print(('FOV point num: ', pc_velo.shape[0]))
    #draw_lidar(pc_velo, fig=fig)
    fig = draw_lidar_simple(pc_velo)
    obj_mean = np.array([0.0,0.0,0.0])
    obj_count = 0
    for obj in objects:
        if obj.type=='DontCare':continue
        # Draw 3d bounding box
        box3d_pts_2d, box3d_pts_3d = utils.compute_box_3d(obj, np.eye(4))#(8,2),(8,3)
        box3d_pts_3d_velo = calib.project_global_to_velo(box3d_pts_3d)
        # box3d_pts_3d_velo = box3d_pts_3d
        # Draw heading arrow
        ori3d_pts_2d, ori3d_pts_3d = utils.compute_orientation_3d(obj, np.eye(4))
        ori3d_pts_3d_velo = calib.project_global_to_velo(ori3d_pts_3d)
        ori3d_pts_3d_velo = ori3d_pts_3d
        x1,y1,z1 = ori3d_pts_3d_velo[0,:]
        x2,y2,z2 = ori3d_pts_3d_velo[1,:]
        draw_gt_boxes3d([box3d_pts_3d_velo], fig=fig)

        mlab.plot3d([x1, x2], [y1, y2], [z1,z2], color=(0.5,0.5,0.5),
            tube_radius=None, line_width=1, figure=fig)

        obj_mean += np.sum(box3d_pts_3d_velo,axis=0)
        obj_count += 1
    obj_mean = obj_mean / obj_count
    print("mean:",obj_mean)
    mlab.show(1)


def translate(points, x: np.ndarray) -> None:
    """
    Applies a translation to the point cloud.
    :param x: <np.float: 3, 1>. Translation in x, y, z.
    """
    for i in range(3):
        points[i, :] = points[i, :] + x[i]


def rotate(points, rot_matrix: np.ndarray) -> None:
    """
    Applies a rotation.
    :param rot_matrix: <np.float: 3, 3>. Rotation matrix.
    """
    points[:3, :] = np.dot(rot_matrix, points[:3, :])
    return points

def show_lidar_on_image(pc_velo, img, calib, view, img_width, img_height):
    ''' Project LiDAR points to image '''
    ipdb.set_trace()
    imgfov_pc_velo, pts_2d, fov_inds = get_lidar_in_image_fov(pc_velo,
        calib, view, 0, 0, img_width, img_height, True)
    imgfov_pts_2d = pts_2d[fov_inds,:]
    imgfov_pc_rect = calib.project_velo_to_rect(imgfov_pc_velo)

    import matplotlib.pyplot as plt
    cmap = plt.cm.get_cmap('hsv', 256)
    cmap = np.array([cmap(i) for i in range(256)])[:,:3]*255

    for i in range(imgfov_pts_2d.shape[0]):
        depth = imgfov_pc_rect[i,2]
        color = cmap[int(640.0/depth),:]
        cv2.circle(img, (int(np.round(imgfov_pts_2d[i,0])),
            int(np.round(imgfov_pts_2d[i,1]))),
            2, color=tuple(color), thickness=-1)
    Image.fromarray(img).show() 
    return img

def dataset_viz():
    dataset = nuscenes2kitti_object(os.path.join(ROOT_DIR, 'dataset/KITTI/object'))

    for data_idx in range(len(dataset)):
        # Load data from dataset
        objects = dataset.get_label_objects(data_idx)
        objects[0].print_object()
        img = dataset.get_image(data_idx)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB) 
        img_height, img_width, img_channel = img.shape
        print(('Image shape: ', img.shape))
        pc_velo = dataset.get_lidar(data_idx)[:,0:3]
        calib = dataset.get_calibration(data_idx)

        # Draw 2d and 3d boxes on image
        show_image_with_boxes(img, objects, calib.CAM_FRONT, False)
        raw_input()
        # Show all LiDAR points. Draw 3d box in LiDAR point cloud
        show_lidar_with_boxes(pc_velo, objects, calib, True, img_width, img_height)
        raw_input()

if __name__=='__main__':
    import mayavi.mlab as mlab
    from viz_util import draw_lidar_simple, draw_lidar, draw_gt_boxes3d
    dataset_viz()
