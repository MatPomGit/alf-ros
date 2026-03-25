from setuptools import find_packages, setup
import os
from glob import glob

package_name = 'alf_ros'

setup(
    name=package_name,
    version='1.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.py')),
        (os.path.join('share', package_name, 'rviz'), glob('rviz/*.rviz')),
        (os.path.join('share', package_name, 'config'), glob('config/*.yaml')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='MatPomGit',
    maintainer_email='contact@example.com',
    description='Full ROS2 communication software with GUI for Unitree G1 EDU',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'gui_node = alf_ros.nodes.gui_node:main',
            'robot_controller = alf_ros.nodes.robot_controller_node:main',
            'status_monitor = alf_ros.nodes.status_monitor_node:main',
        ],
    },
)
