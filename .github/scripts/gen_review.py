#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#          http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
import json
import os
from typing import List

import google.generativeai as genai
import requests
from loguru import logger




def get_review_prompt(extra_prompt: str = "") -> str:
    """Get a prompt template"""
    template = f"""
    This is a pull request or part of a pull request if the pull request is very large.
    Suppose you review this PR as an excellent software engineer and an excellent security engineer.
    Can you tell me the issues with differences in a pull request and provide suggestions to improve it?
    You can provide a review summary and issue comments per file if any major issues are found.
    Always include the name of the file that is citing the improvement or problem.
    In the next messages I will be sending you the difference between the GitHub file codes, okay?
    """
    return template


def get_summarize_prompt() -> str:
    """Get a prompt template"""
    template = """
    Can you summarize this for me?
    It would be good to stick to highlighting pressing issues and providing code suggestions to improve the pull request.
    Please summarize the review in a few sentences, which no longer than 256 words.
    Here's what you need to summarize:
    """
    return template


def create_a_comment_to_pull_request(
    github_token: str,
    github_repository: str,
    pull_request_number: int,
    git_commit_hash: str,
    body: str,
):
    """Create a comment to a pull request"""
    headers = {
        "Accept": "application/vnd.github.v3.patch",
        "authorization": f"Bearer {github_token}",
    }
    data = {"body": body, "commit_id": git_commit_hash, "event": "COMMENT"}
    url = f"https://api.github.com/repos/{github_repository}/pulls/{pull_request_number}/reviews"
    response = requests.post(url, headers=headers, data=json.dumps(data))
    return response


def chunk_string(input_string: str, chunk_size) -> List[str]:
    """Chunk a string"""
    chunked_inputs = []
    for i in range(0, len(input_string), chunk_size):
        chunked_inputs.append(input_string[i : i + chunk_size])
    return chunked_inputs


def get_review(
    model: str,
    diff: str,
    extra_prompt: str,
    temperature: float,
    max_tokens: int,
    top_p: float,
    frequency_penalty: float,
    presence_penalty: float,
    prompt_chunk_size: int,
):
    """Get a review"""
    # Chunk the prompt
    review_prompt = get_review_prompt(extra_prompt=extra_prompt)
    chunked_diff_list = chunk_string(input_string=diff, chunk_size=prompt_chunk_size)
    generation_config = {
        "temperature": 1,
        "top_p": 0.95,
        "top_k": 0,
        "max_output_tokens": 8192,
    }
    genai_model = genai.GenerativeModel(
        model_name=model, generation_config=generation_config
    )
    # Get summary by chunk
    chunked_reviews = []
    for chunked_diff in chunked_diff_list:
        convo = genai_model.start_chat(
            history=[
                {"role": "user", "parts": [review_prompt]},
                {"role": "model", "parts": ["Ok"]},
            ]
        )
        convo.send_message(chunked_diff)
        review_result = convo.last.text
        chunked_reviews.append(review_result)
    # If the chunked reviews are only one, return it

    if len(chunked_reviews) == 1:
        return chunked_reviews, chunked_reviews[0]

    if len(chunked_reviews) == 0:
        summarize_prompt = (
            "Say that you didn't find any relevant changes to comment on any file"
        )
    else:
        summarize_prompt = get_summarize_prompt()

    chunked_reviews_join = "\n".join(chunked_reviews)
    convo = genai_model.start_chat(history=[])
    convo.send_message(summarize_prompt + "\n\n" + chunked_reviews_join)
    summarized_review = convo.last.text
    logger.debug(f"Response AI: {summarized_review}")
    return chunked_reviews, summarized_review


def format_review_comment(summarized_review: str, chunked_reviews: List[str]) -> str:
    """Format reviews"""
    if len(chunked_reviews) == 1:
        return summarized_review
    unioned_reviews = "\n".join(chunked_reviews)
    review = f"""<details>
    <summary>{summarized_review}</summary>
    {unioned_reviews}
    </details>
    """
    return review


def get_review_summary(
    diff: str,
    api_key: str,
    diff_chunk_size=3500,
    model="gemini-1.5-flash",
    extra_prompt="",
    temperature=0.1,
    max_tokens=512,
    top_p=1.0,
    frequency_penalty=0.0,
    presence_penalty=0.0,
    log_level="INFO",
):
    # Set log level
    logger.level(log_level)
    
    # Set the Gemini API key
    genai.configure(api_key=api_key)

    # Request a code review
    chunked_reviews, summarized_review = get_review(
        diff=diff,
        extra_prompt=extra_prompt,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        top_p=top_p,
        frequency_penalty=frequency_penalty,
        presence_penalty=presence_penalty,
        prompt_chunk_size=diff_chunk_size,
    )

    # Format reviews
    review_comment = format_review_comment(
        summarized_review=summarized_review, chunked_reviews=chunked_reviews
    )
    print(review_comment)
    return review_comment
    # # Create a comment to a pull request
    # create_a_comment_to_pull_request(
    #     github_token=os.getenv("GITHUB_TOKEN"),
    #     github_repository=os.getenv("GITHUB_REPOSITORY"),
    #     pull_request_number=int(os.getenv("GITHUB_PULL_REQUEST_NUMBER")),
    #     git_commit_hash=os.getenv("GIT_COMMIT_HASH"),
    #     body=review_comment
    # )
