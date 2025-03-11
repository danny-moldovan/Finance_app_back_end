# Use an official Python runtime as a base image
FROM python:3.9

#Copy over the requirements file
COPY requirements.txt /app/requirements.txt

# Set the working directory in the container
WORKDIR /app

# Install dependencies
RUN pip install -r requirements.txt

# Copy the application code
COPY . .
#COPY .env .env

# Expose the port Flask runs on
EXPOSE 5000

# Command to run the application
CMD ["python", "app.py"]