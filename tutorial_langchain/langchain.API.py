# ---
# jupyter:
#   jupytext:
#     formats: ipynb,py:percent
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.16.7
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# %% [markdown]
# # LangChain API Tutorial
#
# This tutorial demonstrates how to use LangChain's core functionalities.
# LangChain is a powerful framework designed to facilitate building language model-powered applications.
# We'll explore its components, including prompt creation, chains, retrieval, and agents.

# %%
# Use this to enable vim shortcuts.
# # !sudo /bin/bash -c "(source /venv/bin/activate; pip install --quiet jupyterlab-vim)"
# # !jupyter labextension enable

# %%
# %load_ext autoreload
# %autoreload 2

# %% [markdown]
# ## Setting Up
#
# We'll start by setting up the environment and initializing our language model (`ChatOpenAI`).
# Here, we're using OpenAI's `gpt-4o-mini` model with a temperature of 0 for deterministic outputs.

# %%
# #!sudo /venv/bin/pip install langchain --quiet
# #!sudo /venv/bin/pip install -U langchain-community --quiet
# #!sudo /venv/bin/pip install -U langchain-openai --quiet
# #!sudo /venv/bin/pip install -U langchain-core --quiet
# #!sudo /venv/bin/pip install -U langchainhub --quiet
# #!sudo /venv/bin/pip install -U unstructured --quiet
# #!sudo /venv/bin/pip install --quiet chromadb


# %%
import logging
import os
import random
import time

import helpers.hdbg as hdbg
import langchain
import langchain.agents as lngchagents
import langchain.document_loaders.csv_loader as csvloader
import langchain.hub
import langchain.prompts as lngchprmt
import langchain.schema.messages as lnchscme
import langchain.schema.runnable as lngchschrun
import langchain_community.vectorstores as vectorstores
import langchain_core.output_parsers as lngchoutpar
import langchain_openai as lngchopai

# %%
# Avoid messages from OpenAI REST interface.
hdbg.init_logger(verbosity=logging.CRITICAL)

_LOG = logging.getLogger(__name__)

# %% [markdown]
# ## Add your OpenAPI key and initiate GPT model

# %%
# Add OpenAPI to environment variable.
#os.environ["OPENAI_API_KEY"] = ""
# Initiate OpenAI model.
chat_model = lngchopai.ChatOpenAI(model="gpt-4o-mini", temperature=0)

# %% [markdown]
# ## Message Handling with `HumanMessage` and `SystemMessage`
#
# LangChain uses `HumanMessage` and `SystemMessage` objects to structure conversations.
# - **`SystemMessage`**: Defines the behavior of the assistant.
# - **`HumanMessage`**: Represents user input.
#
# Let's see how this works in practice with some example messages.

# %%
# Define system behavior and user input.
messages = [
    lnchscme.SystemMessage(
        content="You're an assistant knowledgeable about healthcare."
    ),
    lnchscme.HumanMessage(content="What is Medicaid managed care?"),
]
# Generate a response.
val = chat_model.invoke(messages)

# %%
type(val)

# %%
print(val.content)

# %%
val.usage_metadata

# %% [markdown]
# ## Restricting Assistant's Scope
#
# You can further control the assistant's responses by tailoring the `SystemMessage`.
# For instance, we'll restrict it to only answer healthcare-related questions.

# %%
messages = [
    lnchscme.SystemMessage(
        content="You're an assistant knowledgeable about healthcare. Only answer healthcare-related questions."
    ),
    lnchscme.HumanMessage(content="How do I change a tire?"),
]
val = chat_model.invoke(messages)
print(val.content)

# %% [markdown]
# ## Creating Custom Prompts with `ChatPromptTemplate`
#
# Custom prompts are essential for tasks like summarization, question answering, or content generation.
# We'll use `ChatPromptTemplate` to define structured prompts and format them dynamically.

# %%
# Define a custom template for hospital reviews.
review_template_str = """
Your job is to use patient reviews to answer questions about their experience at a hospital.
Use the following context to answer questions. Be as detailed as possible, but don't make up
any information that's not from the context. If you don't know an answer, say you don't know.

{context}

{question}
"""

review_template = lngchprmt.ChatPromptTemplate.from_template(review_template_str)

# Provide context and a question.
context = "I had a great stay!"
question = "Did anyone have a positive experience?"

# Format the template.
print(review_template.format(context=context, question=question))

# %% [markdown]
# ## Advanced Prompt Structuring
#
# Sometimes, you may need to structure prompts with multiple components, like system instructions and user input.
# `SystemMessagePromptTemplate` and `HumanMessagePromptTemplate` allow fine-grained control.

# %%
# Define system and human message templates.
review_system_prompt = lngchprmt.SystemMessagePromptTemplate(
    prompt=lngchprmt.PromptTemplate(
        input_variables=["context"], template=review_template_str
    )
)

review_human_prompt = lngchprmt.HumanMessagePromptTemplate(
    prompt=lngchprmt.PromptTemplate(
        input_variables=["question"], template="{question}"
    )
)

# Combine into a chat prompt template.
review_prompt_template = lngchprmt.ChatPromptTemplate(
    input_variables=["context", "question"],
    messages=[review_system_prompt, review_human_prompt],
)

# Format messages.
formatted_messages = review_prompt_template.format_messages(
    context=context, question=question
)
print(formatted_messages)

# %%
print(formatted_messages[0].content)

# %%
print(formatted_messages[1].content)

# %% [markdown]
# ## Chains
#
# Chains are a fundamental abstraction in LangChain, allowing you to combine prompts and models into workflows.
# We'll create a simple chain to answer questions based on a given context.

# %%
# Create a chain using the template and chat model.
output_parser = lngchoutpar.StrOutputParser()
review_chain = review_prompt_template | chat_model | output_parser

# Test the chain.
review_chain.invoke({"context": context, "question": question})

# %% [markdown]
# ## Retrieval with FAISS
#
# FAISS (Facebook AI Similarity Search) is used to efficiently retrieve relevant documents based on similarity scores.
# We'll demonstrate how to load a dataset, create embeddings, and retrieve documents.

# %%
import pandas as pd

REVIEWS_CSV_PATH = "data/reviews.csv"

df = pd.read_csv(REVIEWS_CSV_PATH)
df.head(3)

# %%
len(reviews)

# %%
REVIEWS_CHROMA_PATH = "chroma_data"

# Load reviews dataset.
loader = csvloader.CSVLoader(file_path=REVIEWS_CSV_PATH, source_column="review")
reviews = loader.load()

# Create a vector store.
reviews_vector_db = vectorstores.Chroma.from_documents(
    reviews, lngchopai.OpenAIEmbeddings(), persist_directory=REVIEWS_CHROMA_PATH
)

# %%
# Retrieve relevant documents.
question = "Has anyone complained about communication with the hospital staff?"
relevant_docs = reviews_vector_db.similarity_search(question, k=3)

print("#0\n" + relevant_docs[0].page_content)
print("#1\n" + relevant_docs[1].page_content)
print("#2\n" + relevant_docs[2].page_content)

# %% [markdown]
# ## Building a Retrieval-Enhanced QA Chain
#
# We'll combine retrieval and prompts to build a more dynamic question-answering system.
# This chain retrieves relevant documents and uses them as context for the assistant.

# %%
# Create a retriever.
reviews_retriever = reviews_vector_db.as_retriever(k=10)

# Build the QA chain.
review_chain = (
    {"context": reviews_retriever, "question": lngchschrun.RunnablePassthrough()}
    | review_prompt_template
    | chat_model
    | lngchoutpar.StrOutputParser()
)

# Test the QA chain.
question = "Has anyone complained about communication with the hospital staff?"
#question = "Has anyone complained the price of eggs?"
review_chain.invoke(question)


# %% [markdown]
# ## Agents
#
# Agents are more flexible than chains, as they can decide the sequence of actions to take.
# We'll demonstrate an agent that can answer questions using tools for reviews and wait times.
#
# - The chain is hardwired
# - An agent is an LLM that decides the sequence of actions to execute.


# %%
def get_current_wait_time(hospital: str) -> int | str:
    """
    Dummy function to generate fake wait times.
    """
    if hospital not in ["A", "B", "C", "D"]:
        return f"Hospital {hospital} does not exist"
    # Simulate API call delay.
    time.sleep(1)
    return random.randint(0, 10000)


# %%
# Tool is an interface that an agent uses to interact with a function.
# Each description explains the Agent when to call each tool.
tools = [
    lngchagents.Tool(
        name="Reviews",
        func=review_chain.invoke,
        description="""Useful when you need to answer questions
        about patient reviews or experiences at the hospital.
        Not useful for answering questions about specific visit
        details such as payer, billing, treatment, diagnosis,
        chief complaint, hospital, or physician information.
        Pass the entire question as input to the tool. For instance,
        if the question is "What do patients think about the triage system?",
        the input should be "What do patients think about the triage system?"
        """,
    ),
    lngchagents.Tool(
        name="Waits",
        func=get_current_wait_time,
        description="""Use when asked about current wait times
        at a specific hospital. This tool can only get the current
        wait time at a hospital and does not have any information about
        aggregate or historical wait times. This tool returns wait times in
        minutes. Do not pass the word "hospital" as input,
        only the hospital name itself. For instance, if the question is
        "What is the wait time at hospital A?", the input should be "A".
        """,
    ),
]

hospital_agent_prompt = langchain.hub.pull("hwchase17/openai-functions-agent")

hospital_agent = lngchagents.create_openai_functions_agent(
    llm=chat_model,
    prompt=hospital_agent_prompt,
    tools=tools,
)

# Agent run-time.
hospital_agent_executor = lngchagents.AgentExecutor(
    agent=hospital_agent,
    tools=tools,
    return_intermediate_steps=True,
    verbose=True,
)

# %%
hospital_agent_executor.invoke(
    {"input": "What is the current wait time at hospital C?"}
)

# %%
hospital_agent_executor.invoke(
    {"input": "What have patients said about their comfort at the hospital?"}
)
