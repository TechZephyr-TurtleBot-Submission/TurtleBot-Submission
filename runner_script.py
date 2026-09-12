#!/usr/bin/env python3
import rclpy
from geometry_msgs.msg import PoseStamped
from nav2_simple_commander.robot_navigator import BasicNavigator, TaskResult

def create_pose(navigator, x, y, yaw_deg=0.0):
    """Helper function to create a PoseStamped message."""
    pose = PoseStamped()
    pose.header.frame_id = 'map'
    pose.header.stamp = navigator.get_clock().now().to_msg()
    pose.pose.position.x = float(x)
    pose.pose.position.y = float(y)
    pose.pose.position.z = 0.0
    
    # Convert yaw degrees to orientation quaternion (around Z axis)
    import math
    rad = math.radians(yaw_deg)
    pose.pose.orientation.z = math.sin(rad / 2.0)
    pose.pose.orientation.w = math.cos(rad / 2.0)
    return pose

def main():
    rclpy.init()
    navigator = BasicNavigator(namespace='runner')

    # 1. AUTO-INITIALIZE POSE AT (0, 0, 0)
    # Eliminates the need to click '2D Pose Estimate' in RViz manually!
    initial_pose = create_pose(navigator, 0.0, 0.0, yaw_deg=0.0)
    navigator.setInitialPose(initial_pose)

    # Wait for Nav2 active state
    navigator.waitUntilNav2Active()
    print("Nav2 initialized successfully! Setting max velocity cap...")

    # 2. DEFINE YOUR CUSTOM WAYPOINTS (x, y, heading_angle_in_degrees)
    # EDIT THESE COORDINATES TO DESIGN YOUR OWN PATH AROUND THE ARENA
    waypoint_coords = [
        (-2.0,  0.0,  90.0),   # Waypoint 1: Drive West lane
        (-2.0,  2.2,   0.0),   # Waypoint 2: North-West corner
        ( 2.0,  2.2, -90.0),   # Waypoint 3: North-East corner
        ( 2.0, -2.2, 180.0),   # Waypoint 4: South-East corner
        (-2.0, -2.2,  90.0),   # Waypoint 5: South-West corner
        ( 0.0,  0.0,   0.0),   # Waypoint 6: Return to Center Spawn
    ]

    # Convert coordinates to Nav2 PoseStamped list
    goal_poses = [create_pose(navigator, wp[0], wp[1], wp[2]) for wp in waypoint_coords]

    # 3. EXECUTE WAYPOINTS SEQUENTIALLY
    for idx, goal in enumerate(goal_poses):
        print(f"Navigating to Waypoint {idx + 1}/{len(goal_poses)}: ({waypoint_coords[idx][0]}, {waypoint_coords[idx][1]})")
        
        navigator.goToPose(goal)

        # Monitor goal progress
        while not navigator.isTaskComplete():
            feedback = navigator.getFeedback()
            # Loop delay
            rclpy.spin_once(navigator, timeout_sec=0.1)

        result = navigator.getResult()
        if result == TaskResult.SUCCEEDED:
            print(f"Reached Waypoint {idx + 1}!")
        elif result == TaskResult.CANCELED:
            print("Goal was canceled!")
            break
        elif result == TaskResult.FAILED:
            print(f"Failed to reach Waypoint {idx + 1}. Skipping to next...")

    print("Runner completed the planned path circuit!")
    rclpy.shutdown()

if __name__ == '__main__':
    main()