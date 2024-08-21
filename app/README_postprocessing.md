Calculate Available Tokens:

Objective: Determine the total number of tokens available for the context after accounting for fixed text in the prompt.
Steps:
Count Fixed Text Tokens: Calculate the number of tokens used by the fixed text in the prompt (e.g., instructions or other fixed content).
Determine Remaining Tokens: Subtract the number of tokens used by the fixed text from the total available tokens to get the remaining tokens for context.
Proportionally Split Tokens:

Objective: Allocate the remaining tokens between the previous context and the current context proportionally based on their lengths.
Steps:
Calculate Context Lengths: Measure the lengths (in characters or tokens) of the previous and current contexts.
Allocate Tokens Proportionally: Distribute the remaining tokens between the previous and current contexts based on their relative lengths.
Ensure Natural Speaker Boundary:

Objective: Ensure the previous context starts at a natural speaker boundary to maintain coherence.
Steps:
Identify Speaker Boundaries: Before truncating the previous context, identify where each speaker’s sentence or utterance begins.
Truncate at Boundary: Adjust the truncation so that the previous context starts with a complete speaker’s sentence or utterance, avoiding cuts in the middle of dialogue.
Generate the Prompt:

Objective: Create a coherent prompt that includes both the previous and current contexts within the allocated token limits.
Steps:
Truncate Contexts: Apply the token limits to both the previous and current contexts, ensuring that the previous context starts at a natural speaker boundary.
Compose the Prompt: Combine the fixed text, truncated previous context, and truncated current context to form the final prompt.
Process GPT Output:

Objective: Use the GPT output to map speakers and apply this mapping to the entire current transcription.
Steps:
Send Prompt to GPT: Send the generated prompt to the GPT model.
Identify Speaker Mapping: Analyze the GPT output to identify consistent speaker mapping between the previous and current contexts.
Apply Speaker Mapping: Use the identified mapping to label speakers consistently across the entire current transcription.

Example Workflow:
Calculate Available Tokens:

Fixed text in the prompt uses 50 tokens.
Total available tokens are 4096.
Remaining tokens: 4096 - 50 = 4046.
Proportionally Split Tokens:

Previous context length: 1500 characters.
Current context length: 2000 characters.
Allocate tokens: ~1811 tokens for previous, ~2235 tokens for current context.
Ensure Natural Speaker Boundary:

Identify the last full speaker's sentence in the previous context.
Truncate at this boundary to ensure coherence.
Generate the Prompt:

Combine the fixed text, previous context, and current context within the allocated tokens.
Process GPT Output:

Send the prompt to GPT.
Analyze the response to identify speaker consistency.
Apply consistent speaker labels to the entire current transcription.