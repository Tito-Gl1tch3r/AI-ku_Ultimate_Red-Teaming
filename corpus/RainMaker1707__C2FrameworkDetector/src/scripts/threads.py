from openai import OpenAIError
from os import listdir


question = "Hello world"

"""
Function that return the next network trace in the list todo, and append it in the list done
@params: todo: list of string filepath of the network trace to send.
@params: done: list of already returned network trace filepaths
"""
def define_sample(todo, done=[]):
    done.append(todo.pop())
    return done[-1]


"""
Change the file in the vector 
@params: vector_id: 
@params: sample:
@returns: string: vector id of the LLM knowledge
"""
def change_vector(vector_id, sample):
    pass


"""
Create one thread from the network trace sample
@returns: string: The thread ID to retrieve it after completion
"""
def create_thread(question, client, assistant_id):
    try:
        thread = client.beta.threads.create(
            messages=[{"role": "user", "content": question}]
        )
        run = client.beta.threads.runs.create(
            thread_id = thread.id,
            assistant_id = assistant_id
        )
        return thread.id
    except OpenAIError as e:
        print(f'OpenAI Error:\n{e}')
        return None


"""
Save a line in the output csv file.
@params: thread_id: The id of one thread created by the script.
@params: sample: The network trace sample used to create the thread.
@params: number: The number of the test. Between 0 and configs.number
@params: output: The output file path where the line is append.
@params: separator: default is ",". Can be customized as wanted in the final csv.
"""
def save(thread_id, sample, number, output, separator=","):
    with open(output, 'a') as file:
        to_write = f'{number}{separator}{thread_id}{separator}{sample}\n'
        file.write(to_write)
        file.close()


"""
Create thread, running test for every network trace in the directory and save the thread id in the output csv
@params: configs: file path of the json config file
@params: threads_out: file path of the output file to create. The file will be emptied if existing
@params: network_trace: Network traces directory, without sub directory. All network trace in the same directory.
"""
def create_threads(configs, threads_out, network_trace, client):
    configs, client = config(configs, threads_out, "t", client)
    samples = listdir(network_trace)
    while samples:
        sample = define_sample(samples)
        change_vector(configs.get("vector_id"), sample)
        for i in range(configs.get("tests_number")):
            thread_id = create_thread(question, client, configs.get("assistant_id"))
            save(thread_id, sample, i, threads_out)
            if thread_id is None:
                exit(1)



if __name__ == "__main__":
    import argparse
    from utils import config, connect

    parser = argparse.ArgumentParser()
    parser.add_argument("configs")
    parser.add_argument("threads_out")
    parser.add_argument("network_traces")

    args = parser.parse_args()
    create_threads(args.configs, args.threads_out, args.network_traces, client)

else:
    from scripts.utils import config, connect
    