#!/usr/bin/env python3
import getopt
import socket
import os
import sys
import psutil
import time
import uuid
import argparse
import dockerhelper
import socket
coapPath = os.path.abspath("../../CoAPthon3")
sys.path.insert(1, coapPath)

from coapthon.client.helperclient import HelperClient
from coapthon import defines
#import docker as docker_client

import messages_pb2

client = None
agent_id = str(uuid.getnode())
agent_name = socket.gethostname()
ping_rate = 1000 #ping every 1000ms

tasks = {}

def constructPing(wrapper):
    wrapper.ping.agent.ping_rate = ping_rate
    wrapper.ping.agent.id = agent_id
    wrapper.ping.agent.name = agent_name

    # add CPU
    cpu_resource = wrapper.ping.agent.resources.add()
    cpu_resource.name = "cpus"
    cpu_resource.type = messages_pb2.Value.SCALAR
    cpu_list = psutil.cpu_percent(interval=1,percpu=True)
    cpu_value = 0
    for cpu in cpu_list:
        cpu_value += (100 - cpu)/100
    cpu_resource.scalar.value = cpu_value
    print("CPU Available:")
    print(cpu_resource)

    # add MEMORY
    mem_resource = wrapper.ping.agent.resources.add()
    mem_resource.name = "mem"
    mem_resource.type = messages_pb2.Value.SCALAR
    mem_resource.scalar.value = psutil.virtual_memory().available
    print("Memory Available:")
    print(mem_resource)

    # iterate through the containers and update the state
    for task_id, task in tasks.items():
        if task.container.type == messages_pb2.ContainerInfo.Type.DOCKER:
            task.state = dockerhelper.getContainerStatus(task_id)
            if task.state == messages_pb2.TaskInfo.ERRORED:
                task.error_message = dockerhelper.getContainerLogs(task_id)

    # add the state of tasks to the ping
    wrapper.ping.tasks.extend(tasks.values())
    print(wrapper.ping.tasks)


def main(host, port):  # pragma: no cover
    global client

    try:
        tmp = socket.gethostbyname(host)
        host = tmp
    except socket.gaierror:
        pass
    
    client = HelperClient(server=(host, int(port)))
    

    # construct message
    wrapper = messages_pb2.WrapperMessage()
    constructPing(wrapper)
    register_payload = wrapper.SerializeToString()

    print("Registering with master...")
    print("My Agent ID is " + agent_id)
    print("My Agent name is " + agent_name)

    # loop ping/pong
    try:
        while True:
            time.sleep(ping_rate / 1000)
            wrapper = messages_pb2.WrapperMessage()
            constructPing(wrapper)
            print("")
            print("Ping!")
            ct = {'content_type': defines.Content_types["application/octet-stream"]}
            response = client.post('ping', wrapper.SerializeToString(), timeout=2, **ct)
            if response:
                print("Pong!")
                wrapper = messages_pb2.WrapperMessage()
                wrapper.ParseFromString(response.payload)
                if wrapper.pong.run_task.task.name:
                    if wrapper.pong.run_task.task.container.type == messages_pb2.ContainerInfo.Type.DOCKER:
                        print("Received Docker Task!!")

                        print("Storing task")
                        tasks[wrapper.pong.run_task.task.task_id] = wrapper.pong.run_task.task

                        print("Launching task")
                        #for now just grab the container info. Let ping check the state on the next run
                        containerInfo = dockerhelper.runImageFromRunTask(wrapper.pong.run_task)
                    else:
                        print("Agent cannot run this type of task")

    except KeyboardInterrupt:
        print("Client Shutdown")
        # TODO: Deregister
        client.stop()



if __name__ == '__main__':  # pragma: no cover
    parser = argparse.ArgumentParser(description='Launch the CoAP Resource Manager Agent')
    parser.add_argument('--host', required=True, help='the Master IP to register with.')
    parser.add_argument('--port', required=False, default=5683, help='the Master port to register on.')
    args = parser.parse_args()
    main(args.host, args.port)
    main()
