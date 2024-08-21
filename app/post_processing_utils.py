import openai
from tiktoken import encoding_for_model

# Set model and token limit (e.g., for GPT-3.5-turbo)
MODEL_NAME = "gpt-3.5-turbo"
MAX_TOKENS = 4096  # Model-specific maximum tokens

def count_tokens(text, model_name=MODEL_NAME):
    enc = encoding_for_model(model_name)
    return len(enc.encode(text))

def calculate_token_allocation(previous_text, current_text, fixed_token_count, max_tokens=MAX_TOKENS):
    # Calculate total available tokens after fixed text
    available_tokens = max_tokens - fixed_token_count
    
    # Calculate proportional token allocation
    previous_tokens = count_tokens(previous_text)
    current_tokens = count_tokens(current_text)
    total_context_tokens = previous_tokens + current_tokens
    
    if total_context_tokens > available_tokens:
        prev_ratio = previous_tokens / total_context_tokens
        curr_ratio = current_tokens / total_context_tokens
        
        allocated_prev_tokens = int(available_tokens * prev_ratio)
        allocated_curr_tokens = int(available_tokens * curr_ratio)
    else:
        allocated_prev_tokens = previous_tokens
        allocated_curr_tokens = current_tokens
    
    return allocated_prev_tokens, allocated_curr_tokens

def find_speaker_boundary(text):
    """
    Find the index to start the previous context from a natural speaker boundary.
    """
    # Split the text into lines
    lines = text.splitlines()
    
    # Traverse the lines in reverse to find the last full speaker's utterance
    for i in range(len(lines) - 1, -1, -1):
        if lines[i].startswith("Speaker"):
            # Return the index of this line
            return "\n".join(lines[i:])
    return text  # Return the full text if no speaker boundary found

def generate_proportional_prompt(previous_text, current_text, fixed_prompt_text):
    fixed_token_count = count_tokens(fixed_prompt_text)
    allocated_prev_tokens, allocated_curr_tokens = calculate_token_allocation(previous_text, current_text, fixed_token_count)
    
    # Truncate contexts if necessary
    truncated_previous_text = previous_text[-allocated_prev_tokens:]
    truncated_previous_text = find_speaker_boundary(truncated_previous_text)  # Ensure boundary
    
    truncated_current_text = current_text[-allocated_curr_tokens:]
    
    prompt = f"{fixed_prompt_text}\n\nPrevious context:\n{truncated_previous_text}\n\nCurrent text:\n{truncated_current_text}\n\nPlease identify and map speakers consistently across these contexts."
    return prompt


def map_speakers_and_apply_mapping(gpt_response, speaker_memory):
    new_speaker_info = []
    current_mapping = {}

    for line in gpt_response.splitlines():
        if line.startswith("Speaker"):
            speaker_id, text = line.split(":", 1)
            # If the speaker is new, map it to a consistent ID
            if speaker_id not in speaker_memory:
                new_id = f"Speaker {len(speaker_memory) + 1}"
                speaker_memory[speaker_id] = new_id
                current_mapping[speaker_id] = new_id
            else:
                current_mapping[speaker_id] = speaker_memory[speaker_id]
            new_speaker_info.append(f"{current_mapping[speaker_id]}:{text.strip()}")

    # Apply the mapping to the entire current transcription
    mapped_transcription = "\n".join([f"{current_mapping.get(line.split(':', 1)[0], line.split(':', 1)[0])}:{line.split(':', 1)[1].strip()}" for line in gpt_response.splitlines() if line.startswith("Speaker")])
    
    return mapped_transcription, new_speaker_info, speaker_memory

def transcribe_with_context_and_mapping(previous_text, current_text, speaker_memory):
    # Generate the prompt
    fixed_prompt_text = "Please ensure that speakers are consistently identified across the previous and current contexts."
    prompt = generate_proportional_prompt(previous_text, current_text, fixed_prompt_text)
    
    # Call the GPT model
    response = openai.ChatCompletion.create(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1000,
        temperature=0.5
    )
    
    gpt_response = response.choices[0].message["content"]
    mapped_transcription, new_speaker_info, updated_speaker_memory = map_speakers_and_apply_mapping(gpt_response, speaker_memory)
    
    return mapped_transcription, new_speaker_info, updated_speaker_memory

# Example usage
previous_text = "Some text from the previous chunk..."
current_text = "Text from the current chunk..."
speaker_memory = {}

mapped_transcription, new_speaker_info, updated_speaker_memory = transcribe_with_context_and_mapping(previous_text, current_text, speaker_memory)

