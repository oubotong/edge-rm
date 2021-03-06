import messages_pb2
import threading
import time
import uuid
from google.protobuf.json_format import MessageToDict

#agents stores the original protobuf
#agentsDict stores extra information about the agent
#both are indexed by agent_id
agents = {}
agentsDict = {}

#same for tasks
tasks = {}

#same for frameworks
frameworks = {}
frameworksDict = {}

def get_offer_id():
    return str(uuid.uuid4())

def refresh_agent(aid, agent):
    agent.id = aid
    agents[aid] = agent
    if aid not in agentsDict:
        agentsDict[aid] = {}
        agentsDict[aid]['lastPing'] = time.time()*1000
    else:
        agentsDict[aid]['lastPing'] = time.time()*1000

    return aid

def refresh_tasks(new_tasks):
    #update teh tasks
    for task in new_tasks:
        #if the task already exists
        if task.task_id in tasks and task.state:
            tasks[task.task_id].state = task.state
            if task.error_message:
                tasks[task.task_id].error_message = task.error_message
        else:
            #if it doesn't
            tasks[task.task_id] = task

def add_task(runtaskmsg):
    task_id = runtaskmsg.task.task_id

    # Save the task and update state
    tasks[task_id] = runtaskmsg.task
    tasks[task_id].state = messages_pb2.TaskInfo.TaskState.UNISSUED

    # At the same time add the frameworks
    framework_id = runtaskmsg.task.framework.framework_id
    frameworks[framework_id] = runtaskmsg.task.framework

    return task_id

def get_tasks_by_agent(agent_id):
    tasks_by_agent = []
    for task_id, task in tasks.items():
        if task.agent_id == agent_id:
            tasks_by_agent.append(task)

    return tasks_by_agent
    
def get_next_unissued_task_by_agent(agent_id):
    for task_id, task in tasks.items():
        if task.agent_id == agent_id and task.state == messages_pb2.TaskInfo.TaskState.UNISSUED:
            task.state = messages_pb2.TaskInfo.TaskState.ISSUED
            return task

def get_all_tasks():
    return tasks.values()

def get_all_tasks_as_dict():
    tasks_as_dict = {}
    for task_id, task in tasks.items():
        tasks_as_dict[task_id] = MessageToDict(task)

    return tasks_as_dict.values()

def get_all_agents():
    return agents.values()

def get_all_agents_as_dict():
    agents_as_dict = {}
    for agent_id, agent in agents.items():
        agents_as_dict[agent_id] = MessageToDict(agent)
        agents_as_dict[agent_id].update(agentsDict[agent_id])

    return agents_as_dict.values()

def get_all_frameworks():
    return frameworks.values()

def get_all_frameworks_as_dict():
    frameworks_as_dict = {}
    for framework_id, framework in frameworks.items():
        frameworks_as_dict[framework_id] = MessageToDict(framework)

    return frameworks_as_dict.values()

def clear_stale_agents():
    agents_to_remove = []
    for agent_id in agents.keys():
        ping_rate = 5000
        if agents[agent_id].ping_rate:
            ping_rate = agents[agent_id].ping_rate
        elapsed = time.time() * 1000 - agentsDict[agent_id]['lastPing']
        if elapsed > ping_rate * 2:
            agents_to_remove.append(agent_id)
    for agent_id in agents_to_remove:
        print("Deleting agent " + str(agent_id))
        del agents[agent_id]
        del agentsDict[agent_id]
