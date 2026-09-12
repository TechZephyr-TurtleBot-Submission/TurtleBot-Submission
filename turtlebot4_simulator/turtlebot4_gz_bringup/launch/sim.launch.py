# Copyright 2023 Clearpath Robotics, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# ... [Keep original license header] ...

import os
from pathlib import Path

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, SetEnvironmentVariable
from launch.conditions import IfCondition, UnlessCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node

ARGUMENTS = [
    DeclareLaunchArgument('use_sim_time', default_value='true',
                          choices=['true', 'false'],
                          description='use_sim_time'),
    DeclareLaunchArgument('world', default_value='warehouse',
                          description='Simulation World'),
    DeclareLaunchArgument('model', default_value='lite',
                          choices=['standard', 'lite'],
                          description='Turtlebot4 Model'),
    DeclareLaunchArgument('headless', default_value='false',
                          choices=['true', 'false'],
                          description='Run Gazebo headless (no GUI interface)'),
    DeclareLaunchArgument('verbosity', default_value='2',
                          choices=['1', '2', '3', '4'],
                          description='Gazebo log verbosity level'),
]


def generate_launch_description():

    # Directories
    pkg_turtlebot4_gz_bringup = get_package_share_directory('turtlebot4_gz_bringup')
    pkg_turtlebot4_gz_gui_plugins = get_package_share_directory('turtlebot4_gz_gui_plugins')
    pkg_turtlebot4_description = get_package_share_directory('turtlebot4_description')
    pkg_irobot_create_description = get_package_share_directory('irobot_create_description')
    pkg_irobot_create_gz_bringup = get_package_share_directory('irobot_create_gz_bringup')
    pkg_irobot_create_gz_plugins = get_package_share_directory('irobot_create_gz_plugins')
    pkg_ros_gz_sim = get_package_share_directory('ros_gz_sim')

    # Safely append to Gazebo resource paths instead of completely overwriting system paths
    existing_resource_path = os.environ.get('GZ_SIM_RESOURCE_PATH', '')
    new_resource_paths = [
        os.path.join(pkg_turtlebot4_gz_bringup, 'worlds'),
        os.path.join(pkg_irobot_create_gz_bringup, 'worlds'),
        str(Path(pkg_turtlebot4_description).parent.resolve()),
        str(Path(pkg_irobot_create_description).parent.resolve())
    ]
    if existing_resource_path:
        new_resource_paths.append(existing_resource_path)

    gz_resource_path = SetEnvironmentVariable(
        name='GZ_SIM_RESOURCE_PATH',
        value=':'.join(new_resource_paths)
    )

    existing_gui_path = os.environ.get('GZ_GUI_PLUGIN_PATH', '')
    new_gui_paths = [
        os.path.join(pkg_turtlebot4_gz_gui_plugins, 'lib'),
        os.path.join(pkg_irobot_create_gz_plugins, 'lib')
    ]
    if existing_gui_path:
        new_gui_paths.append(existing_gui_path)

    gz_gui_plugin_path = SetEnvironmentVariable(
        name='GZ_GUI_PLUGIN_PATH',
        value=':'.join(new_gui_paths)
    )

    gz_sim_launch = PathJoinSubstitution([pkg_ros_gz_sim, 'launch', 'gz_sim.launch.py'])

    # Standard GUI Execution (If headless:=false)
    gazebo_gui = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([gz_sim_launch]),
        condition=UnlessCondition(LaunchConfiguration('headless')),
        launch_arguments=[
            ('gz_args', [
                LaunchConfiguration('world'), '.sdf',
                ' -r',
                ' -v ', LaunchConfiguration('verbosity'),
                ' --gui-config ',
                PathJoinSubstitution([
                    pkg_turtlebot4_gz_bringup,
                    'gui',
                    LaunchConfiguration('model'),
                    'gui.config'
                ])
            ])
        ]
    )

    # Headless Server-Only Execution (If headless:=true)
    gazebo_headless = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([gz_sim_launch]),
        condition=IfCondition(LaunchConfiguration('headless')),
        launch_arguments=[
            ('gz_args', [
                LaunchConfiguration('world'), '.sdf',
                ' -r -s',  # '-s' runs server only without starting OGRE2 GUI
                ' -v ', LaunchConfiguration('verbosity')
            ])
        ]
    )

    # Clock bridge
    clock_bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        name='clock_bridge',
        output='screen',
        arguments=['/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock']
    )

    ld = LaunchDescription(ARGUMENTS)
    ld.add_action(gz_resource_path)
    ld.add_action(gz_gui_plugin_path)
    ld.add_action(gazebo_gui)
    ld.add_action(gazebo_headless)
    ld.add_action(clock_bridge)
    return ld