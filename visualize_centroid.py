#!/usr/bin/env python3
import math
import rclpy
from rclpy.node import Node
from rclpy.time import Time
from geometry_msgs.msg import Point
from nav_msgs.msg import Odometry
from visualization_msgs.msg import Marker, MarkerArray

class GlitchFreeVisualizer(Node):
    def __init__(self):
        super().__init__('glitch_free_visualizer')

        self.marker_pub = self.create_publisher(MarkerArray, '/rviz_visualizer_markers', 10)
        self.sub_odom = self.create_subscription(Odometry, '/runner/odom', self.odom_callback, 10)

        self.current_x = 0.0
        self.current_y = 0.0

        # Publish at 20 Hz
        self.timer = self.create_timer(0.05, self.publish_markers)
        self.get_logger().info("Base Link Visualizer active on /rviz_visualizer_markers")

    def odom_callback(self, msg: Odometry):
        self.current_x = msg.pose.pose.position.x
        self.current_y = msg.pose.pose.position.y

    def publish_markers(self):
        marker_array = MarkerArray()
        
        # TIME ZERO STAMP: Fixes RViz TF desync flickering!
        zero_stamp = Time().to_msg()

        # 1. Centroid Point (Red Sphere)
        centroid = Marker()
        centroid.header.frame_id = 'runner/base_link'
        centroid.header.stamp = zero_stamp
        centroid.ns = 'centroid'
        centroid.id = 0
        centroid.type = Marker.SPHERE
        centroid.action = Marker.ADD
        centroid.pose.position.x = 0.0
        centroid.pose.position.y = 0.0
        centroid.pose.position.z = 0.08  # Above robot center
        centroid.scale.x = 0.08
        centroid.scale.y = 0.08
        centroid.scale.z = 0.08
        centroid.color.r = 1.0
        centroid.color.g = 0.0
        centroid.color.b = 0.0
        centroid.color.a = 1.0
        marker_array.markers.append(centroid)

        # 2. Centroid Coordinate Text Display
        text_marker = Marker()
        text_marker.header.frame_id = 'runner/base_link'
        text_marker.header.stamp = zero_stamp
        text_marker.ns = 'coordinate_text'
        text_marker.id = 1
        text_marker.type = Marker.TEXT_VIEW_FACING
        text_marker.action = Marker.ADD
        text_marker.pose.position.x = 0.0
        text_marker.pose.position.y = 0.0
        text_marker.pose.position.z = 0.40  # Elevated high above robot
        text_marker.scale.z = 0.18
        text_marker.color.r = 1.0
        text_marker.color.g = 1.0
        text_marker.color.b = 1.0
        text_marker.color.a = 1.0
        text_marker.text = f"Centroid: ({self.current_x:.2f}, {self.current_y:.2f})"
        marker_array.markers.append(text_marker)

        # 3. 0.5m Radius Circle Ring
        circle_marker = Marker()
        circle_marker.header.frame_id = 'runner/base_link'
        circle_marker.header.stamp = zero_stamp
        circle_marker.ns = 'circle_0_5m'
        circle_marker.id = 2
        circle_marker.type = Marker.LINE_STRIP
        circle_marker.action = Marker.ADD
        circle_marker.scale.x = 0.025  # Thicker line for solid visibility
        circle_marker.color.r = 0.0
        circle_marker.color.g = 1.0
        circle_marker.color.b = 0.0
        circle_marker.color.a = 1.0

        radius = 0.5
        num_points = 48  # Higher resolution circle
        for i in range(num_points + 1):
            angle = 2.0 * math.pi * i / num_points
            p = Point()
            p.x = radius * math.cos(angle)
            p.y = radius * math.sin(angle)
            p.z = 0.05  # Raised slightly to avoid ground clipping
            circle_marker.points.append(p)

        marker_array.markers.append(circle_marker)

        self.marker_pub.publish(marker_array)

def main(args=None):
    rclpy.init(args=args)
    node = GlitchFreeVisualizer()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()