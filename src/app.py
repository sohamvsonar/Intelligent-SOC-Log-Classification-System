import streamlit as st
import pandas as pd

from processor_regex import regex_classify
from processor_bert import bert_classify
from processor_llm  import llm_classify

def classify(logs):
    labels = []
    for source, log_msg in logs:
        label = classify_log(source, log_msg)
        labels.append(label)
    return labels

def classify_log(source, log_message):
    if source == "LegacyCRM":
        label = llm_classify(log_message)
    else:
        label = regex_classify(log_message)
        if label is None:
            label = bert_classify(log_message)
    return label

def classify_csv(input_file):
    df = pd.read_csv(input_file)

    # Perform classification
    df["target_label"] = classify(list(zip(df["source"], df["log_message"])))

    # Save the modified file
    output_file = "../resources/output.csv"
    df.to_csv(output_file, index=False)

    return output_file


def main():
    st.title("Log Message Classification")

    st.write("Download Test Dataset:")
    test_dataset_file = "test.csv"
    test_dataset_url = "../resources/test.csv"  # replace with the actual URL

    with open(test_dataset_url, "rb") as f:
        test_dataset_bytes = f.read()

    st.download_button(
        label="Download Test Dataset",
        data=test_dataset_bytes,
        file_name=test_dataset_file,
        mime="text/csv"
    )

    st.write("Upload a CSV file to classify the log messages:")
    input_file = st.file_uploader("Upload CSV file", type="csv")

    if input_file is not None:
        output_file = classify_csv(input_file)

        st.write("Classification results:")
        df = pd.read_csv(output_file)
        st.write(df)

        st.write("Download the modified CSV file with the target labels:")
        st.download_button(
            label="Download CSV",
            data=df.to_csv(index=False),
            file_name=output_file,
            mime="text/csv",
        )


if __name__ == "__main__":
    main()