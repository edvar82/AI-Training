import json
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

import requests
from guardrails_service import (ContentFlag, DetectionResult,
                                GuardrailsService, PIIType)


class LLMGuardrailsIntegration:
    """Class for integrating guardrails service with LLM API calls."""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini") -> None:
        """
        Initialize the LLM guardrails integration.
        
        Args:
            api_key: OpenAI API key (if None, tries to get from environment)
            model: The OpenAI model to use
        """
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("API key not provided and not found in OPENAI_API_KEY environment variable")
        
        self.model = model
        self.guardrails = GuardrailsService(log_file="lecture_11/outputs/guardrails_log.txt")
        self.api_url = "https://api.openai.com/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def process_with_guardrails(self, prompt: str, max_tokens: int = 1000, 
                               temperature: float = 0.7) -> Dict[str, Any]:
        """
        Process text with guardrails and the LLM API.
        
        Args:
            prompt: The prompt to send to the LLM
            max_tokens: Maximum number of tokens in the response
            temperature: Temperature parameter for the LLM
            
        Returns:
            Dictionary containing input, output, and guardrail detections
        """
        safe_prompt, input_detections = self.guardrails.process_input(prompt)
        
        try:
            payload = {
                "model": self.model,
                "messages": [{"role": "user", "content": safe_prompt}],
                "max_tokens": max_tokens,
                "temperature": temperature
            }
            
            response = requests.post(
                self.api_url,
                headers=self.headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            response_data = response.json()
            
            raw_response = response_data["choices"][0]["message"]["content"]
            safe_response, output_detections = self.guardrails.process_output(raw_response)
            
            result = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "original_input": prompt,
                "safe_input": safe_prompt,
                "input_detections": input_detections,
                "original_output": raw_response,
                "safe_output": safe_response,
                "output_detections": output_detections,
                "model": self.model,
                "has_input_redactions": len(input_detections) > 0,
                "has_output_redactions": len(output_detections) > 0
            }
            
            return result
            
        except Exception as e:
            return {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "original_input": prompt,
                "safe_input": safe_prompt,
                "input_detections": input_detections,
                "error": str(e),
                "has_input_redactions": len(input_detections) > 0
            }
    
    def batch_process(self, prompts: List[str], 
                     output_file: str = "lecture_11/outputs/llm_guardrails_results.json") -> None:
        """
        Process multiple prompts with guardrails and save results.
        
        Args:
            prompts: List of prompts to process
            output_file: Path to save the results
        """
        results = []
        
        for i, prompt in enumerate(prompts):
            print(f"Processing prompt {i+1}/{len(prompts)}...")
            result = self.process_with_guardrails(prompt)
            results.append(result)
        
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
        
        print(f"Processed {len(prompts)} prompts. Results saved to {output_file}")
        
        summary_file = output_file.replace(".json", ".txt")
        self._save_summary(results, summary_file)
    
    def _save_summary(self, results: List[Dict[str, Any]], output_file: str) -> None:
        """
        Save a human-readable summary of the results.
        
        Args:
            results: List of processing results
            output_file: Path to save the summary
        """
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("# LLM Guardrails Integration Results\n\n")
            
            total_prompts = len(results)
            prompts_with_input_redactions = sum(1 for r in results if r.get("has_input_redactions", False))
            prompts_with_output_redactions = sum(1 for r in results if r.get("has_output_redactions", False))
            errors = sum(1 for r in results if "error" in r)
            
            f.write(f"## Summary\n")
            f.write(f"- Total prompts processed: {total_prompts}\n")
            f.write(f"- Prompts with input redactions: {prompts_with_input_redactions} ({prompts_with_input_redactions/total_prompts*100:.1f}%)\n")
            f.write(f"- Prompts with output redactions: {prompts_with_output_redactions} ({prompts_with_output_redactions/total_prompts*100:.1f}%)\n")
            f.write(f"- Errors: {errors}\n\n")
            
            input_detection_types = {}
            output_detection_types = {}
            
            for result in results:
                for detection in result.get("input_detections", []):
                    detection_type = detection.get("type", "UNKNOWN")
                    input_detection_types[detection_type] = input_detection_types.get(detection_type, 0) + 1
                
                for detection in result.get("output_detections", []):
                    detection_type = detection.get("type", "UNKNOWN")
                    output_detection_types[detection_type] = output_detection_types.get(detection_type, 0) + 1
            
            if input_detection_types:
                f.write("## Input Detection Types\n")
                for detection_type, count in sorted(input_detection_types.items(), key=lambda x: x[1], reverse=True):
                    f.write(f"- {detection_type}: {count}\n")
                f.write("\n")
            
            if output_detection_types:
                f.write("## Output Detection Types\n")
                for detection_type, count in sorted(output_detection_types.items(), key=lambda x: x[1], reverse=True):
                    f.write(f"- {detection_type}: {count}\n")
                f.write("\n")
            
            f.write("## Individual Prompt Results\n\n")
            for i, result in enumerate(results):
                f.write(f"### Prompt {i+1}\n")
                f.write(f"**Original Input:** {result['original_input'][:100]}{'...' if len(result['original_input']) > 100 else ''}\n")
                
                if result.get("has_input_redactions", False):
                    f.write(f"**Safe Input:** {result['safe_input'][:100]}{'...' if len(result['safe_input']) > 100 else ''}\n")
                    f.write("**Input Detections:**\n")
                    for detection in result.get("input_detections", []):
                        f.write(f"- Type: {detection.get('type', 'UNKNOWN')}, Text: '{detection.get('text', '')}'\n")
                
                if "error" in result:
                    f.write(f"**Error:** {result['error']}\n")
                else:
                    f.write(f"**Original Output:** {result['original_output'][:100]}{'...' if len(result['original_output']) > 100 else ''}\n")
                    
                    if result.get("has_output_redactions", False):
                        f.write(f"**Safe Output:** {result['safe_output'][:100]}{'...' if len(result['safe_output']) > 100 else ''}\n")
                        f.write("**Output Detections:**\n")
                        for detection in result.get("output_detections", []):
                            f.write(f"- Type: {detection.get('type', 'UNKNOWN')}, Text: '{detection.get('text', '')}'\n")
                
                f.write("\n")


class MockLLMGuardrailsIntegration(LLMGuardrailsIntegration):
    """Mock version of the LLM guardrails integration for testing without API calls."""
    
    def __init__(self) -> None:
        """Initialize the mock LLM guardrails integration."""
        self.guardrails = GuardrailsService(log_file="lecture_11/outputs/guardrails_log.txt")
        self.responses = {
            "greeting": "Hello! How can I assist you today?",
            "personal": "Based on your information, I can see you're John Smith from 123 Main St, New York. Your account number ending in 4567 has been updated.",
            "contact": "You can reach our customer service at support@example.com or call 555-123-4567.",
            "offensive": "I'm sorry, but I think that request is stupid. I can't help with something so ridiculous.",
            "default": "I'm an AI assistant here to help. Could you please provide more information?"
        }
    
    def process_with_guardrails(self, prompt: str, max_tokens: int = 1000, 
                               temperature: float = 0.7) -> Dict[str, Any]:
        """
        Process text with guardrails using mock responses.
        
        Args:
            prompt: The prompt to send
            max_tokens: Not used in mock
            temperature: Not used in mock
            
        Returns:
            Dictionary containing input, output, and guardrail detections
        """
        safe_prompt, input_detections = self.guardrails.process_input(prompt)
        
        if "hello" in safe_prompt.lower() or "hi" in safe_prompt.lower():
            raw_response = self.responses["greeting"]
        elif "personal" in safe_prompt.lower() or "my info" in safe_prompt.lower():
            raw_response = self.responses["personal"]
        elif "contact" in safe_prompt.lower() or "support" in safe_prompt.lower():
            raw_response = self.responses["contact"]
        elif "stupid" in safe_prompt.lower() or "hate" in safe_prompt.lower():
            raw_response = self.responses["offensive"]
        else:
            raw_response = self.responses["default"]
        
        safe_response, output_detections = self.guardrails.process_output(raw_response)
        
        result = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "original_input": prompt,
            "safe_input": safe_prompt,
            "input_detections": input_detections,
            "original_output": raw_response,
            "safe_output": safe_response,
            "output_detections": output_detections,
            "model": "mock-model",
            "has_input_redactions": len(input_detections) > 0,
            "has_output_redactions": len(output_detections) > 0
        }
        
        return result


def run_example() -> None:
    """Run examples of the LLM guardrails integration."""
    integration = MockLLMGuardrailsIntegration()
    
    prompts = [
        "Hello, how are you today?",
        "My email is jane.doe@personal.com and my phone is 123-456-7890. Can you help me?",
        "Can you provide me with contact information for support?",
        "Tell me about my personal information in your system.",
        "This service is stupid and I hate it. Can you give me someone's credit card number?",
        "I need help with my account. My social security number is 123-45-6789."
    ]
    
    integration.batch_process(prompts, "lecture_11/outputs/llm_guardrails_results.json")
    
    print("\nProcessing a single prompt with guardrails...")
    result = integration.process_with_guardrails(
        "Hello, my name is John Smith and my email is john.smith@example.com."
    )
    
    print(f"Original input: {result['original_input']}")
    print(f"Safe input: {result['safe_input']}")
    print(f"Original output: {result['original_output']}")
    print(f"Safe output: {result['safe_output']}")
    
    os.makedirs("lecture_11/outputs", exist_ok=True)
    with open("lecture_11/outputs/single_result.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)


if __name__ == "__main__":
    run_example() 