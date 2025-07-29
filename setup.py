from setuptools import setup, find_packages

setup(
    name='bheem-project_management',
    version='1.0.0',
    packages=find_packages(include=["project_management", "project_management.*"]),
    install_requires=[],
    include_package_data=True,
    description='Bheem Project_management ERP module',
    author='Bheem Core Team',
    url='https://github.com/bheemverse/Bheem_Project_management'
)
