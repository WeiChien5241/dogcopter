import os
from glob import glob

from setuptools import find_packages, setup

package_name = 'flight_robot_pkg'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'),
            glob('flight_robot_pkg/launch/*.launch.py')
            + glob('flight_robot_pkg/launch/*.sh')
            + ['flight_robot_pkg/launch/simulation-gazebo.py']),
        (os.path.join('share', package_name, 'config'),
            glob('flight_robot_pkg/config/*.yaml')),
        (os.path.join('share', package_name, 'worlds'),
            glob('flight_robot_pkg/worlds/*.sdf')),
        (os.path.join('share', package_name, 'airframes'),
            glob('flight_robot_pkg/airframes/*')),
        # Only the live model files; the other .sdf files in that directory
        # are historical scratch variants and stay out of the install.
        (os.path.join('share', package_name, 'models', 'flight_robot'),
            ['flight_robot_pkg/models/flight_robot/model.sdf',
             'flight_robot_pkg/models/flight_robot/model.config']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='weichien241',
    maintainer_email='weichien241@gmail.com',
    description='DogCopter hybrid drive-and-fly vehicle: Gazebo model, PX4 airframe, ROS 2 bridge and mode manager',
    license='MIT',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
        ],
    },
)
