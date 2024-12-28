"""Setup file for the Timewise Guardian Windows client."""
from setuptools import find_packages, setup
import os
from pathlib import Path

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

def install_service():
    """Install the Windows service."""
    import win32serviceutil
    import win32service
    try:
        win32serviceutil.InstallService(
            None,
            "TimeWiseGuardian",
            "TimeWise Guardian Monitor",
            startType=win32service.SERVICE_AUTO_START,
            exeName=sys.executable,
            pythonClassString="twg.service.TWGService"
        )
        print("Service installed successfully")
    except Exception as e:
        print(f"Failed to install service: {e}")

def remove_service():
    """Remove the Windows service."""
    import win32serviceutil
    try:
        win32serviceutil.RemoveService("TimeWiseGuardian")
        print("Service removed successfully")
    except Exception as e:
        print(f"Failed to remove service: {e}")

setup(
    name="timewise-guardian-client",
    version="0.1.0",
    author="Kim Asplund",
    author_email="kim.asplund@gmail.com",
    description="Windows client for Timewise Guardian - A Home Assistant integration for monitoring computer usage",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/kimasplund/timewise-guardian",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: Microsoft :: Windows",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "twg-monitor=twg.monitor:main",
            "twg-service=twg.service:run_service",
        ],
    },
    cmdclass={
        "install_service": install_service,
        "remove_service": remove_service,
    },
    data_files=[
        (os.path.join(os.environ.get("PROGRAMDATA", ""), "TimeWiseGuardian"), [
            "twg/config.yaml"
        ])
    ]
) 