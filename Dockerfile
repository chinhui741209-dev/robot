# Use NVIDIA JetPack base image (or standard Ubuntu if cross-compiling/sim)
# For AGX Orin, we typically use nvcr.io/nvidia/l4t-jetpack
FROM ubuntu:22.04

# Prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# Install ROS 2 Humble
RUN apt-get update && apt-get install -y \
    curl \
    gnupg2 \
    lsb-release \
    && curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key -o /usr/share/keyrings/ros-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(lsb_release -cs) main" | tee /etc/apt/sources.list.d/ros2.list > /dev/null \
    && apt-get update && apt-get install -y \
    ros-humble-ros-base \
    ros-dev-tools \
    python3-colcon-common-extensions \
    && rm -rf /var/lib/apt/lists/*

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3-pip \
    liblcm-dev \
    python3-tk \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set up workspace
ENV POC_ROOT=/workspace/robot
WORKDIR $POC_ROOT

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy the rest of the code
COPY . .

# Initialize rosdep
RUN rosdep init || true && rosdep update

# Install ROS 2 dependencies
RUN apt-get update && \
    rosdep install --from-paths . --ignore-src -r -y --rosdistro humble && \
    rm -rf /var/lib/apt/lists/*

# Build C++ packages
RUN . /opt/ros/humble/setup.sh && \
    colcon build --symlink-install

# Set up entrypoint
RUN echo "source /opt/ros/humble/setup.bash" >> ~/.bashrc && \
    echo "source $POC_ROOT/install/setup.bash" >> ~/.bashrc

ENTRYPOINT ["/bin/bash"]
