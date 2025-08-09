#!/bin/bash
set -e

echo "--- Starting Docker Installation ---"

# 1. Set up Docker's repository
echo "--- Step 1: Setting up Docker's repository ---"

# Update the apt package index and install packages to allow apt to use a repository over HTTPS
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg

# Add Docker’s official GPG key
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

# Set up the repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

echo "--- Repository setup complete ---"

# 2. Install Docker Engine
echo "--- Step 2: Installing Docker Engine ---"

# Update the apt package index
sudo apt-get update

# Install Docker Engine, CLI, containerd, and Docker Compose plugin
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

echo "--- Docker Engine installation complete ---"

# 3. (Recommended) Manage Docker as a non-root user
echo "--- Step 3: Configuring Docker to run as a non-root user ---"

# Create the docker group if it doesn't already exist
if ! getent group docker > /dev/null; then
    sudo groupadd docker
fi

# Add your user to the docker group
sudo usermod -aG docker $USER

echo "--- Configuration complete ---"

echo "">> Docker installation successful! <<"
echo "IMPORTANT: You must log out and log back in for the group changes to take effect."
echo "After logging back in, you can verify the installation by running: docker run hello-world"
