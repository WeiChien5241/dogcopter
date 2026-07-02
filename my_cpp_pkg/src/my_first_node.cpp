#include "rclcpp/rclcpp.hpp"

int main(int argc, char **argv)
{
    rclcpp::init(argc, argv); //initialize ros2 communication, init function
    auto node = std::make_shared<rclcpp::Node>();
    rclcpp::shutdown();
    return 0;
}