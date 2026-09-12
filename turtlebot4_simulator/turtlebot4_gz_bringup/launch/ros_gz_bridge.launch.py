# Copyright 2023 Clearpath Robotics, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# ... [Keep your original license header here] ...

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import EqualsSubstitution, LaunchConfiguration
from launch.substitutions.path_join_substitution import PathJoinSubstitution

from launch_ros.actions import Node

ARGUMENTS = [
    DeclareLaunchArgument('use_sim_time', default_value='true',
                          choices=['true', 'false'],
                          description='Use sim time'),
    DeclareLaunchArgument('robot_name', default_value='turtlebot4',
                          description='Gazebo model name'),
    DeclareLaunchArgument('dock_name', default_value='standard_dock',
                          description='Gazebo model name'),
    DeclareLaunchArgument('namespace', default_value='',
                          description='Robot namespace'),
    DeclareLaunchArgument('world', default_value='warehouse',
                          description='World name'),
    DeclareLaunchArgument('model', default_value='standard',
                          choices=['standard', 'lite'],
                          description='Turtlebot4 Model'),
]


def generate_launch_description():
    use_sim_time = LaunchConfiguration('use_sim_time')
    robot_name = LaunchConfiguration('robot_name')
    # dock_name = LaunchConfiguration('dock_name')
    namespace = LaunchConfiguration('namespace')
    world = LaunchConfiguration('world')

    # leds = ['power', 'motors', 'comms', 'wifi', 'battery', 'user1', 'user2']

    pkg_irobot_create_gz_bringup = get_package_share_directory('irobot_create_gz_bringup')
    create3_ros_gz_bridge_launch = PathJoinSubstitution(
        [pkg_irobot_create_gz_bringup, 'launch', 'create3_ros_gz_bridge.launch.py'])

    create3_bridge = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([create3_ros_gz_bridge_launch]),
        launch_arguments=[
            ('robot_name', robot_name),
            # ('dock_name', dock_name),
            ('namespace', namespace),
            ('world', world)
        ]
    )

    # =========================================
    # OPTIMIZATION 1: Combined Sensor Bridge
    # Merges Lidar and OAK-D camera into a single node
    # =========================================
    sensor_bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        name='sensor_bridge',
        output='screen',
        parameters=[{'use_sim_time': use_sim_time}],
        arguments=[
            # Lidar
            ['/world/', world, '/model/', robot_name, '/link/rplidar_link/sensor/rplidar/scan@sensor_msgs/msg/LaserScan[gz.msgs.LaserScan'],
            # Camera Image
            ['/world/', world, '/model/', robot_name, '/link/oakd_rgb_camera_frame/sensor/rgbd_camera/image@sensor_msgs/msg/Image[gz.msgs.Image'],
            # Camera Depth
            ['/world/', world, '/model/', robot_name, '/link/oakd_rgb_camera_frame/sensor/rgbd_camera/depth_image@sensor_msgs/msg/Image[gz.msgs.Image'],
            # Camera Points
            ['/world/', world, '/model/', robot_name, '/link/oakd_rgb_camera_frame/sensor/rgbd_camera/points@sensor_msgs/msg/PointCloud2[gz.msgs.PointCloudPacked'],
            # Camera Info
            ['/world/', world, '/model/', robot_name, '/link/oakd_rgb_camera_frame/sensor/rgbd_camera/camera_info@sensor_msgs/msg/CameraInfo[gz.msgs.CameraInfo'],
        ],
        remappings=[
            (['/world/', world, '/model/', robot_name, '/link/rplidar_link/sensor/rplidar/scan'], 'scan'),
            (['/world/', world, '/model/', robot_name, '/link/oakd_rgb_camera_frame/sensor/rgbd_camera/image'], 'oakd/rgb/preview/image_raw'),
            (['/world/', world, '/model/', robot_name, '/link/oakd_rgb_camera_frame/sensor/rgbd_camera/depth_image'], 'oakd/rgb/preview/depth'),
            (['/world/', world, '/model/', robot_name, '/link/oakd_rgb_camera_frame/sensor/rgbd_camera/points'], 'oakd/rgb/preview/depth/points'),
            (['/world/', world, '/model/', robot_name, '/link/oakd_rgb_camera_frame/sensor/rgbd_camera/camera_info'], 'oakd/rgb/preview/camera_info')
        ]
    )

    # =========================================
    # OPTIMIZATION 2: Combined HMI Bridge
    # Merges Buttons, Display, and all LEDs into one conditional node
    # =========================================
    # hmi_args = [
    #     [namespace, '/hmi/display/raw@std_msgs/msg/String]gz.msgs.StringMsg'],
    #     [namespace, '/hmi/display/selected@std_msgs/msg/Int32]gz.msgs.Int32'],
    #     [namespace, '/hmi/buttons@std_msgs/msg/Int32[gz.msgs.Int32'],
    # ]
    # hmi_args.extend([[namespace, '/hmi/led/' + led + '@std_msgs/msg/Int32]gz.msgs.Int32'] for led in leds])

    # hmi_remappings = [
    #     ([namespace, '/hmi/display/raw'], 'hmi/display/_raw'),
    #     ([namespace, '/hmi/display/selected'], 'hmi/display/_selected'),
    #     ([namespace, '/hmi/buttons'], 'hmi/buttons/_set'),
    # ]
    # hmi_remappings.extend([([namespace, '/hmi/led/' + led], 'hmi/led/_' + led) for led in leds])

    # hmi_bridge = Node(
    #     package='ros_gz_bridge',
    #     executable='parameter_bridge',
    #     name='hmi_bridge',
    #     output='screen',
    #     parameters=[{'use_sim_time': use_sim_time}],
    #     condition=IfCondition(EqualsSubstitution(LaunchConfiguration('model'), 'standard')),
    #     arguments=hmi_args,
    #     remappings=hmi_remappings
    # )

    # Define LaunchDescription variable
    ld = LaunchDescription(ARGUMENTS)
    ld.add_action(create3_bridge)
    ld.add_action(sensor_bridge)
    # ld.add_action(hmi_bridge)
    
    return ld