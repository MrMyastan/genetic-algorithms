# slightly modified from https://github.com/paraschopra/deepneuroevolution and their 
# great tutorial https://towardsdatascience.com/reinforcement-learning-without-gradients-evolving-agents-using-genetic-algorithms-8685817d84f

# To add a new cell, type '# %%'
# To add a new markdown cell, type '# %% [markdown]'
# %%
import gym
import numpy as np
import torch
import time


# %%
from gym.wrappers import Monitor


# %%
from torch import randn_like
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim


# %%
import math
import copy

game_actions = 2 #2 actions possible: left or right

# %%
class CartPoleAI(nn.Module):
        def __init__(self):
            super().__init__()
            self.fc = nn.Sequential(
                        nn.Linear(4,128, bias=True),
                        nn.ReLU(),
                        nn.Linear(128,2, bias=True),
                        nn.Softmax(dim=1)
                        )

                
        def forward(self, inputs):
            x = self.fc(inputs)
            return x


# %%
def init_weights(m):
    
        # nn.Conv2d weights are of shape [16, 1, 3, 3] i.e. # number of filters, 1, stride, stride
        # nn.Conv2d bias is of shape [16] i.e. # number of filters
        
        # nn.Linear weights are of shape [32, 24336] i.e. # number of input features, number of output features
        # nn.Linear bias is of shape [32] i.e. # number of output features
        
        if ((type(m) == nn.Linear) | (type(m) == nn.Conv2d)):
            nn.init.xavier_uniform(m.weight)
            m.bias.data.fill_(0.00)
            


# %%
def return_random_agents(num_agents) -> "list[CartPoleAI]":
    
    agents = []
    for _ in range(num_agents):
        
        agent = CartPoleAI()
        
        for param in agent.parameters():
            param.requires_grad = False
            
        init_weights(agent)
        agents.append(agent)
        
        
    return agents
    


# %%
def run_agents(agents):
    
    reward_agents = []
    env = gym.make("CartPole-v0")
    
    for agent in agents:
        agent.eval()
    
        observation = env.reset()
        
        r=0
        s=0
        
        for _ in range(250):
            
            inp = torch.tensor(observation).type('torch.FloatTensor').view(1,-1)
            output_probabilities = agent(inp).detach().numpy()[0]
            action = np.random.choice(range(game_actions), 1, p=output_probabilities).item()
            new_observation, reward, done, info = env.step(action)
            r+=reward
            
            s+=1
            observation = new_observation

            if(done):
                break

        reward_agents.append(r)        
        #reward_agents.append(s)
        
    
    return reward_agents


# %%
def return_average_score(agent, runs):
    score = 0.
    for i in range(runs):
        score += run_agents([agent])[0]
    return score/runs


# %%
def run_agents_n_times(agents, runs):
    avg_score = []
    for agent in agents:
        avg_score.append(return_average_score(agent,runs))
    return avg_score


# %%
def mutate(agent) -> CartPoleAI:

    child_agent = copy.deepcopy(agent)
    
    mutation_power = 0.02 #hyper-parameter, set from https://arxiv.org/pdf/1712.06567.pdf
            
    for param in child_agent.parameters():
        noise = randn_like(param.data)
        param.data = param.data.add(noise, alpha=mutation_power)

    return child_agent


# %%
def return_children(agents, sorted_parent_indexes, elite_index):
    
    children_agents = []
    
    #first take selected parents from sorted_parent_indexes and generate N-1 children
    for i in range(len(agents)-1):
        selected_agent_index = sorted_parent_indexes[np.random.randint(len(sorted_parent_indexes))]
        children_agents.append(mutate(agents[selected_agent_index]))

    #now add one elite
    elite_child = add_elite(agents, sorted_parent_indexes, elite_index)
    children_agents.append(elite_child)
    elite_index=len(children_agents)-1 #it is the last one
    
    return children_agents, elite_index


# %%
def add_elite(agents, sorted_parent_indexes, elite_index=None, only_consider_top_n=10):
    
    candidate_elite_index = sorted_parent_indexes[:only_consider_top_n]
    
    if(elite_index is not None):
        candidate_elite_index = np.append(candidate_elite_index,[elite_index])
        
    top_score = 0
    top_elite_index = None
    
    for i in candidate_elite_index:
        score = return_average_score(agents[i],runs=5)
        print("Score for elite i ", i, " is ", score)
        
        
        if(score > top_score):
            top_score = score
            top_elite_index = i
            
    print("Elite selected with index ",top_elite_index, " and score", top_score)
    
    child_agent = copy.deepcopy(agents[top_elite_index])
    return child_agent


# %%
def train(generations, num_agents=500, top_limit=20):
    #disable gradients as we will not use them
    torch.set_grad_enabled(False)

    agents = return_random_agents(num_agents)

    # top limit = How many top agents to consider as parents
    
    elite_index = None

    for generation in range(generations):

        # return rewards of agents
        rewards = run_agents_n_times(agents, 3) #return average of 3 runs

        # sort by rewards
        sorted_parent_indexes = np.argsort(rewards)[::-1][:top_limit] #reverses and gives top values (argsort sorts by ascending by default) https://stackoverflow.com/questions/16486252/is-it-possible-to-use-argsort-in-descending-order
        print("")
        print("")
        
        top_rewards = []
        for best_parent in sorted_parent_indexes:
            top_rewards.append(rewards[best_parent])
        
        print("Generation ", generation, " | Mean rewards: ", np.mean(rewards), " | Mean of top 5: ",np.mean(top_rewards[:5]))
        #print(rewards)
        print("Top ",top_limit," scores", sorted_parent_indexes)
        print("Rewards for top: ",top_rewards)
        
        # setup an empty list for containing children agents
        children_agents, elite_index = return_children(agents, sorted_parent_indexes, elite_index)

        # kill all agents, and replace them with their children
        agents = children_agents
    if elite_index is None:
        elite_index = 0
    return agents, elite_index


# %%
def play_agent(agent):
    #try and exception block because, render hangs if an erorr occurs, we must do env.close to continue working    
    env = gym.make("CartPole-v0")
    
    observation = env.reset()
    last_observation = observation
    r=0
    while True:
        env.render()
        inp = torch.tensor(observation).type('torch.FloatTensor').view(1,-1)
        print(agent(inp).requires_grad)
        output_probabilities = agent(inp).detach().numpy()[0]
        action = np.random.choice(range(game_actions), 1, p=output_probabilities).item()
        new_observation, reward, done, info = env.step(action)
        r+=reward
        observation = new_observation

        if(done):
            break

    env.close()
    print("Rewards: ",r)      


# %%

choice = input("What do? ")
if choice == "train":
    agents, elite_index = train(generations=int(input("how much train? ")))
    torch.save(agents[elite_index].state_dict(), "./fully_trained.pt")
    play_agent(agents[elite_index])
if choice == "play":
    model = CartPoleAI()
    model.load_state_dict(torch.load("./fully_trained.pt"))
    play_agent(model)

