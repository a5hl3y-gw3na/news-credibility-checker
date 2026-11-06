# 📰 AI-Powered News Credibility Checker

An intelligent news credibility assessment system that combines Machine Learning, Natural Language Processing (NLP), metadata analysis, and evidence retrieval to evaluate the credibility of online news articles.

## 📌 Project Overview

The News Credibility Checker is an AI-powered browser extension designed to help users assess the reliability of online news content.

The system analyses article text, publisher information, language patterns, and supporting evidence from external sources to identify potential misinformation and credibility concerns.

Rather than automatically declaring an article true or false, the system provides an evidence-based credibility assessment, highlighting potential warning signs and explaining its findings.

## 🎯 Project Objectives

- Develop a machine learning model capable of classifying news articles using labelled datasets.
- Apply NLP techniques to identify linguistic patterns associated with potentially misleading content.
- Analyse article metadata, including publisher information, author details, publication dates, and domain information.
- Retrieve relevant external evidence to support or challenge claims made in news articles.
- Develop a browser extension that allows users to analyse online articles in real time.
- Present transparent results with explanations, evidence links, and uncertainty indicators.

## 🧠 Core Technologies

| Technology | Purpose |
|---|---|
| Python | Core development language |
| Scikit-learn | Machine learning and classification |
| TF-IDF | Text feature extraction |
| Logistic Regression | Baseline news classification model |
| NLP | Linguistic pattern analysis |
| FastAPI | Backend API and model integration |
| Google Colab | Model development and experimentation |
| JavaScript | Browser extension functionality |
| HTML/CSS | Extension interface |
| GitHub | Version control and collaboration |

## ⚙️ System Architecture

The system consists of five major components:

1. **Text Classification:** Analyses article text using a trained machine learning model.
2. **Metadata Analysis:** Examines publisher domains, authorship, publication dates, and available article information.
3. **Language Analysis:** Identifies sensational, emotionally loaded, and potentially misleading language patterns.
4. **Evidence Retrieval:** Retrieves relevant information from external sources to compare against article claims.
5. **Browser Extension:** Provides an accessible interface for analysing articles directly from the browser.

## 🔬 Machine Learning Approach

The initial machine learning implementation uses:

- TF-IDF for converting article text into numerical features.
- Logistic Regression for baseline classification.
- Labelled news datasets for supervised learning.
- Precision, Recall, F1-score, and Confusion Matrix for model evaluation.

The baseline model will be developed and evaluated in Google Colab before integration into the FastAPI backend.

## 🖥️ Planned Browser Extension

Users will be able to:

1. Open an online news article.
2. Activate the News Credibility Checker extension.
3. Select **Analyse Article**.
4. Allow the system to extract available article content and metadata.
5. Receive a credibility assessment with supporting explanations and evidence links.

## ⚠️ Responsible AI

The system is designed as a decision-support tool, not an absolute truth detector.

A machine learning prediction, missing metadata, or sensational language does not independently establish that an article is false.

When supporting evidence is unavailable or inconclusive, the system will communicate uncertainty rather than generate an unsupported verdict.

## 🚧 Project Status

Currently under development.

The project will progressively implement the machine learning pipeline, metadata and language analysis, evidence retrieval, FastAPI backend, and browser extension.

---

**Project Category:** Artificial Intelligence & Intelligent Systems  
**Focus Areas:** Machine Learning | Natural Language Processing | Information Credibility | Browser Automation | Evidence-Based Analysis
