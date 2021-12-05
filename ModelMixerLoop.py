#!/usr/bin/env python
# coding: utf-8

# In[1]:


import gc
import torch
import numpy as np
from transformers import AutoTokenizer, DataCollatorWithPadding, DataCollatorForLanguageModeling
from transformers import AutoModelForSequenceClassification, TrainingArguments, Trainer
from datasets import load_dataset, load_metric
import transformers
import os

gc.collect()
torch.cuda.empty_cache()

metric_collector = []


# List of glue tasks
#GLUE_TASKS = ["cola", "mnli", "mnli-mm", "mrpc", "qnli", "qqp", "rte", "sst2", "stsb", "wnli"]
GLUE_TASKS = ["cola", "mnli", "mnli-mm", "mrpc", "qnli", "qqp", "rte", "sst2",  "wnli"]
#GLUE_TASKS = ["qqp"]


# In[ ]:



for task in GLUE_TASKS:
    
    #List of glue keys
    task_to_keys = {
        "cola": ("sentence", None),
        "mnli": ("premise", "hypothesis"),
        "mnli-mm": ("premise", "hypothesis"),
        "mrpc": ("sentence1", "sentence2"),
        "qnli": ("question", "sentence"),
        "qqp": ("question1", "question2"),
        "rte": ("sentence1", "sentence2"),
        "sst2": ("sentence", None),
        "stsb": ("sentence1", "sentence2"),
        "wnli": ("sentence1", "sentence2"),
    }
    
    #Select task
    #task = "rte"  #cola, mrpc
    batch_size = 10 #10 normally, 8 for qnli
    
    # Load dataset based on task variable
    actual_task = "mnli" if task == "mnli-mm" else task
    dataset = load_dataset("glue", actual_task)
    metric = load_metric('glue', actual_task)
    
    #Collect sentence keys and labels
    sentence1_key, sentence2_key = task_to_keys[task]
    
    # Number of logits to output
    num_labels = 3 if task.startswith("mnli") else 1 if task=="stsb" else 2
    
    

    ###############################################
    
    #         DEBERTA SECTION
    
    ###############################################
    
    
    ###  Tokenizing Section  ####
    
    #Load model
    model_checkpoint = "microsoft/deberta-v3-small"
    
    # Create tokenizer for respective model
    tokenizer = AutoTokenizer.from_pretrained(model_checkpoint, use_fast=True, truncation=True, model_max_length=512)
    
    def tokenizer_func(examples):
        if sentence2_key is None:
            return tokenizer(examples[sentence1_key], truncation=True,)
        return tokenizer(examples[sentence1_key], examples[sentence2_key], truncation=True,)
    
    # tokenize sentence(s)
    encoded_dataset = dataset.map(tokenizer_func, batched=True)
    
    #model_checkpoint = "deberta-v3-small_baseline_cola/"
    model_checkpoint = "deberta-v3-small_baseline_"+actual_task+"/"
    
    ###  Model Section  ####
    
    # Create model and attach ForSequenceClassification head
    model_deberta = AutoModelForSequenceClassification.from_pretrained(model_checkpoint, num_labels=num_labels)
    
    # Type of metric for given task
    metric_name = "pearson" if task == "stsb" else "matthews_correlation" if task == "cola" else "accuracy"
    
    args = TrainingArguments(
        f"{model_checkpoint}-finetuned-Testing-{task}",
        evaluation_strategy = "epoch",
        per_device_eval_batch_size=batch_size,
        weight_decay=0.01,
        metric_for_best_model=metric_name,
        eval_accumulation_steps=5
    )
    
    def compute_metrics(eval_pred):
        predictions, labels = eval_pred
        if task != "stsb":
            predictions = np.argmax(predictions, axis=1)
        else:
            predictions = predictions[:, 0]
        return metric.compute(predictions=predictions, references=labels)
    
    validation_key = "validation_mismatched" if task == "mnli-mm" else "validation_matched" if task == "mnli" else "validation"
    trainer = Trainer(
        model_deberta,
        args,
        train_dataset=encoded_dataset["train"],
        eval_dataset=encoded_dataset[validation_key],
        tokenizer=tokenizer,
        compute_metrics=compute_metrics
    )
    
    trainer.evaluate()
    

    
    ### Collect Predictions  ###
    
    prediction_deberta = trainer.predict(encoded_dataset[validation_key])
    

    
    ## Clear the Cache
    gc.collect()
    torch.cuda.empty_cache()
    
    
    ###############################################
    
    #         ELECTRA SECTION
    
    ###############################################
    
    
    ###  Tokenizing Section  ####
    
    #Load model
    model_checkpoint = "google/electra-small-discriminator"
    
    # Create tokenizer for respective model
    tokenizer = AutoTokenizer.from_pretrained(model_checkpoint, use_fast=True, truncation=True, model_max_length=512)
    
    def tokenizer_func(examples):
        if sentence2_key is None:
            return tokenizer(examples[sentence1_key], truncation=True,)
        return tokenizer(examples[sentence1_key], examples[sentence2_key], truncation=True,)
    
    # tokenize sentence(s)
    encoded_dataset = dataset.map(tokenizer_func, batched=True)
    
    #model_checkpoint = "electra-small-discriminator-finetuned-cola/"
    #model_checkpoint = "Electra_fintuned_cola/"
    model_checkpoint = "Electra_fintuned_"+actual_task+"/"
    
    ###  Model Section  ####
    
    # Create model and attach ForSequenceClassification head
    model_electra = AutoModelForSequenceClassification.from_pretrained(model_checkpoint, num_labels=num_labels)
    
    # Type of metric for given task
    metric_name = "pearson" if task == "stsb" else "matthews_correlation" if task == "cola" else "accuracy"
    
    
    args = TrainingArguments(
        f"{model_checkpoint}-finetuned-Testing-{task}",
        evaluation_strategy = "epoch",
        per_device_eval_batch_size=batch_size,
        weight_decay=0.01,
        metric_for_best_model=metric_name,
        eval_accumulation_steps=5
    )
    
    def compute_metrics(eval_pred):
        predictions, labels = eval_pred
        if task != "stsb":
            predictions = np.argmax(predictions, axis=1)
        else:
            predictions = predictions[:, 0]
        return metric.compute(predictions=predictions, references=labels)
    
    validation_key = "validation_mismatched" if task == "mnli-mm" else "validation_matched" if task == "mnli" else "validation"
    trainer = Trainer(
        model_electra,
        args,
        train_dataset=encoded_dataset["train"],
        eval_dataset=encoded_dataset[validation_key],
        tokenizer=tokenizer,
        compute_metrics=compute_metrics
    )
    
    trainer.evaluate()
    
    

    
    ### Collect Predictions  ###
    ## Clear the Cache
    gc.collect()
    torch.cuda.empty_cache()
    prediction_electra = trainer.predict(encoded_dataset[validation_key])
    

    
    
    ## Clear the Cache
    gc.collect()
    torch.cuda.empty_cache()
    


    ###############################################
    
    #         XLNET SECTION
    
    ###############################################
    
    
    ###  Tokenizing Section  ####
    
    #Load model
    model_checkpoint = "xlnet-base-cased"
    
    # Create tokenizer for respective model
    tokenizer = AutoTokenizer.from_pretrained(model_checkpoint, use_fast=True, truncation=True, model_max_length=512)
    
    def tokenizer_func(examples):
        if sentence2_key is None:
            return tokenizer(examples[sentence1_key], truncation=True,)
        return tokenizer(examples[sentence1_key], examples[sentence2_key], truncation=True,)
    
    # tokenize sentence(s)
    encoded_dataset = dataset.map(tokenizer_func, batched=True)
    
    #model_checkpoint = "electra-small-discriminator-finetuned-cola/"
    #model_checkpoint = "Electra_fintuned_cola/"
    model_checkpoint = "xlnet-base-cased_baseline_"+actual_task+"/"
    
    ###  Model Section  ####
    
    # Create model and attach ForSequenceClassification head
    model_xlnet = AutoModelForSequenceClassification.from_pretrained(model_checkpoint, num_labels=num_labels)
    
    # Type of metric for given task
    metric_name = "pearson" if task == "stsb" else "matthews_correlation" if task == "cola" else "accuracy"
    
    
    args = TrainingArguments(
        f"{model_checkpoint}-finetuned-Testing-{task}",
        evaluation_strategy = "epoch",
        per_device_eval_batch_size=batch_size,
        weight_decay=0.01,
        metric_for_best_model=metric_name,
        eval_accumulation_steps=5
    )
    
    def compute_metrics(eval_pred):
        predictions, labels = eval_pred
        if task != "stsb":
            predictions = np.argmax(predictions, axis=1)
        else:
            predictions = predictions[:, 0]
        return metric.compute(predictions=predictions, references=labels)
    
    validation_key = "validation_mismatched" if task == "mnli-mm" else "validation_matched" if task == "mnli" else "validation"
    trainer = Trainer(
        model_xlnet,
        args,
        train_dataset=encoded_dataset["train"],
        eval_dataset=encoded_dataset[validation_key],
        tokenizer=tokenizer,
        compute_metrics=compute_metrics
    )
    
    trainer.evaluate()
    

    
    ### Collect Predictions  ###
    ## Clear the Cache
    gc.collect()
    torch.cuda.empty_cache()
    prediction_xlnet = trainer.predict(encoded_dataset[validation_key])
    

    
    ## Clear the Cache
    gc.collect()
    torch.cuda.empty_cache()
    

    
    

    ###############################################
    
    # Combine Model Predicions to create Input Features
    
    ###############################################
    
    
    import pandas as pd
    
    #Labels
    val_labels = prediction_deberta.label_ids
    
    
    #DeBERTa
    df_deberta = pd.DataFrame(prediction_deberta[0])
    df_deberta=df_deberta.rename(columns=dict(zip(df_deberta.columns,['deberta_'+str(col) for col in df_deberta.columns])))
    print(df_deberta.head(),'\n')
    
    
    #Electra
    df_electra = pd.DataFrame(prediction_electra[0])
    df_electra=df_electra.rename(columns=dict(zip(df_electra.columns,['electra_'+str(col) for col in df_electra.columns])))
    print(df_electra.head(),'\n')
    
    
    #XLNet
    df_xlnet = pd.DataFrame(prediction_xlnet[0])
    df_xlnet=df_xlnet.rename(columns=dict(zip(df_xlnet.columns,['xlnet_'+str(col) for col in df_xlnet.columns])))
    print(df_xlnet.head(),'\n')
    
    

    
    
    #Combine the dataframes
    df_combine = pd.concat([df_deberta, df_electra, df_xlnet], axis=1)
    df_combine.head()
    
    
    ###############################################
    
    #         ENSEMBLE SECTION
    
    ###############################################
    
    
    # Importing the required packages
    
    from sklearn.model_selection import train_test_split
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.metrics import confusion_matrix
    from sklearn.metrics import accuracy_score
    from sklearn.metrics import f1_score
    from sklearn.metrics import matthews_corrcoef
    from sklearn.metrics import classification_report
    from sklearn.metrics import roc_auc_score
    

    
    # Split the dataset into train and test
    
    X_train, X_test, y_train, y_test = train_test_split(df_combine, val_labels, test_size=0.3, random_state=100)
    X_train.head()
    
    
    # Perform training with random forest with all columns
    # Initialize random forest classifier
    clf = RandomForestClassifier(n_estimators=100)
    
    # Perform training
    clf.fit(X_train, y_train)
    
    # Predicton on test using all features
    y_pred = clf.predict(X_test)
    y_pred_score = clf.predict_proba(X_test)
    

    
    # Print basic Report, then specify for the model
    
    print("\n")
    print("Results Using All Features: \n")
    
    print("Classification Report: ")
    print(classification_report(y_test,y_pred))
    print("\n")
    
    if metric_name == 'accuracy':
        ensemble_score = accuracy_score(y_test, y_pred)
        try:
            ensemble_f = f1_score(y_test, y_pred)
        except:
            pass
    
    elif metric_name == 'matthews_correlation':
        ensemble_score = matthews_corrcoef(y_test, y_pred)
        ensemble_f = 999
    
    elif metric_name == "pearson":
        ensemble_score = accuracy_score(y_test, y_pred)
        ensemble_f = 999
    else:
        ensemble_score = 999
        ensemble_f = 999
        print('ERROR')
    
    if ensemble_f != 999:
        deberta_f = prediction_deberta.metrics['test_f1'], 
        electra_f = prediction_electra.metrics['test_f1'], 
        xlnet_f = prediction_xlnet.metrics['test_f1']
    else:
        deberta_f = electra_f = xlnet_f = 999
    
    print("Accuracy : ", ensemble_score * 100, '\nFscore : ', ensemble_f)
        
    print('-------------------')
    print("DeBERTa : ", prediction_deberta.metrics['test_'+metric_name]*100)
    print("Electra : ", prediction_electra.metrics['test_'+metric_name]*100)
    print("XLNet : ", prediction_xlnet.metrics['test_'+metric_name]*100)
    
    
    metric_collector.append([task,
                             ensemble_score,
                             prediction_deberta.metrics['test_'+metric_name], 
                             prediction_electra.metrics['test_'+metric_name], 
                             prediction_xlnet.metrics['test_'+metric_name],
                             ensemble_f, deberta_f, electra_f, xlnet_f])
    


# In[ ]:


print('Done')


# In[ ]:


ensemble_metrics = pd.DataFrame(metric_collector, columns = ['Task','Ensemble', 'DeBERTa', 'Electra', 'XLNet', 
                                                             'Ensemble_f','DeBERTa_f', 'Electra_f', 'XLNet_f', ])
ensemble_metrics.head()


# In[ ]:




