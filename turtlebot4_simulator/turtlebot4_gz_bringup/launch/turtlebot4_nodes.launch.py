# Copyright 2023 Clearpath Robotics, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# ... [Keep original license header] ...

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node

# Retrieve share directory outside or lazily inside
pkg_turtlebot4_gz_bringup = get_package_share_directory('turtlebot4_gz_bringup')

ARGUMENTS = [
    DeclareLaunchArgument('use_sim_time', default_value='true',
                          choices=['true', 'false'],
                          description='Use simulation (Gazebo) clock if true'),
    DeclareLaunchArgument('model', default_value='standard',
                          choices=['standard', 'lite'],
                          description='Turtlebot4 Model'),
    DeclareLaunchArgument('param_file',
                          default_value=PathJoinSubstitution(
                              [pkg_turtlebot4_gz_bringup, 'config', 'turtlebot4_node.yaml']),
                          description='Turtlebot4 Robot param file'),
]


def generate_launch_description():
    use_sim_time = LaunchConfiguration('use_sim_time')
    model = LaunchConfiguration('model')
    turtlebot4_node_yaml_file = LaunchConfiguration('param_file')

    # Turtlebot4 status node with sim time explicitly forced
    turtlebot4_node = Node(
        package='turtlebot4_node',
        name='turtlebot4_node',
        executable='turtlebot4_node',
        parameters=[
            turtlebot4_node_yaml_file,
            {
                'model': model,
                'use_sim_time': use_sim_time
            }
        ],
        output='screen',
    )

    ld = LaunchDescription(ARGUMENTS)
    ld.add_action(turtlebot4_node)
    
    return ld