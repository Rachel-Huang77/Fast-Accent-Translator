import torch
import sys
from transformers import AutoTokenizer, AutoModelForMaskedLM


# model_id = 'hfl/chinese-roberta-wwm-ext-large'
local_path = "./bert/chinese-roberta-wwm-ext-large"


tokenizers = {}
models = {}

def get_bert_feature(text, word2ph, device=None, model_id='hfl/chinese-roberta-wwm-ext-large'):
    if (
        sys.platform == "darwin"
        and torch.backends.mps.is_available()
        and device == "cpu"
    ):
        device = "mps"
    if not device:
        device = "cuda"
    
    if model_id not in models:
        if device == "cuda":
            if torch.cuda.is_available():
                print(f"[BERT] 🚀 GPU acceleration enabled: {model_id} -> {torch.cuda.get_device_name(0)}")
            else:
                device = "cpu"
                print(f"[BERT] ⚠️  CUDA unavailable, falling back to CPU mode: {model_id}")
        elif device == "mps":
            print(f"[BERT] 🚀 GPU acceleration enabled: {model_id} -> MPS (Apple Silicon)")
        else:
            print(f"[BERT] ⚠️  Using CPU mode: {model_id}")
        models[model_id] = AutoModelForMaskedLM.from_pretrained(
            model_id
        ).to(device)
        tokenizers[model_id] = AutoTokenizer.from_pretrained(model_id)
    model = models[model_id]
    tokenizer = tokenizers[model_id]

    with torch.no_grad():
        inputs = tokenizer(text, return_tensors="pt")
        for i in inputs:
            inputs[i] = inputs[i].to(device)
        res = model(**inputs, output_hidden_states=True)
        res = torch.cat(res["hidden_states"][-3:-2], -1)[0].cpu()
    # import pdb; pdb.set_trace()
    # assert len(word2ph) == len(text) + 2
    word2phone = word2ph
    phone_level_feature = []
    for i in range(len(word2phone)):
        repeat_feature = res[i].repeat(word2phone[i], 1)
        phone_level_feature.append(repeat_feature)

    phone_level_feature = torch.cat(phone_level_feature, dim=0)
    return phone_level_feature.T


if __name__ == "__main__":
    import torch

    word_level_feature = torch.rand(38, 1024)  # 12 words, each word has 1024-dimensional features
    word2phone = [
        1,
        2,
        1,
        2,
        2,
        1,
        2,
        2,
        1,
        2,
        2,
        1,
        2,
        2,
        2,
        2,
        2,
        1,
        1,
        2,
        2,
        1,
        2,
        2,
        2,
        2,
        1,
        2,
        2,
        2,
        2,
        2,
        1,
        2,
        2,
        2,
        2,
        1,
    ]

    # Calculate total frames
    total_frames = sum(word2phone)
    print(word_level_feature.shape)
    print(word2phone)
    phone_level_feature = []
    for i in range(len(word2phone)):
        print(word_level_feature[i].shape)

        # Repeat each word word2phone[i] times
        repeat_feature = word_level_feature[i].repeat(word2phone[i], 1)
        phone_level_feature.append(repeat_feature)

    phone_level_feature = torch.cat(phone_level_feature, dim=0)
    print(phone_level_feature.shape)  # torch.Size([36, 1024])
