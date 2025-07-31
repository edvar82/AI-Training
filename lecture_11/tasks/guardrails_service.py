import json
import re
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Pattern, Set, Tuple, Union


class PIIType(Enum):
    """Enum representing different types of Personally Identifiable Information."""
    EMAIL = "EMAIL"
    PHONE_NUMBER = "PHONE_NUMBER"
    CREDIT_CARD = "CREDIT_CARD"
    SSN = "SSN"
    ADDRESS = "ADDRESS"
    NAME = "NAME"
    IP_ADDRESS = "IP_ADDRESS"
    DATE_OF_BIRTH = "DATE_OF_BIRTH"
    PASSPORT_NUMBER = "PASSPORT_NUMBER"
    DRIVER_LICENSE = "DRIVER_LICENSE"
    UNKNOWN = "UNKNOWN"


class ContentFlag(Enum):
    """Enum representing different types of potentially harmful content."""
    PROFANITY = "PROFANITY"
    HATE_SPEECH = "HATE_SPEECH"
    VIOLENCE = "VIOLENCE"
    SEXUAL_CONTENT = "SEXUAL_CONTENT"
    SELF_HARM = "SELF_HARM"
    PERSONAL_ATTACK = "PERSONAL_ATTACK"
    MISINFORMATION = "MISINFORMATION"


class DetectionResult:
    """Class representing the result of a PII or harmful content detection."""
    
    def __init__(self, 
                 text: str, 
                 start_pos: int, 
                 end_pos: int, 
                 detected_type: Union[PIIType, ContentFlag],
                 confidence: float = 1.0) -> None:
        """
        Initialize a detection result.
        
        Args:
            text: The detected text
            start_pos: Start position in the original text
            end_pos: End position in the original text
            detected_type: Type of the detected content (PII or harmful content)
            confidence: Confidence score of the detection (0.0 to 1.0)
        """
        self.text = text
        self.start_pos = start_pos
        self.end_pos = end_pos
        self.detected_type = detected_type
        self.confidence = confidence
    
    def __repr__(self) -> str:
        """Return string representation of the detection result."""
        return (f"DetectionResult(text='{self.text}', "
                f"type={self.detected_type}, "
                f"pos=({self.start_pos}, {self.end_pos}), "
                f"confidence={self.confidence:.2f})")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the detection result to a dictionary."""
        return {
            "text": self.text,
            "start_pos": self.start_pos,
            "end_pos": self.end_pos,
            "type": self.detected_type.value,
            "confidence": self.confidence
        }


class PIIDetector:
    """Class for detecting Personally Identifiable Information (PII) in text."""
    
    def __init__(self, custom_patterns: Optional[Dict[PIIType, List[str]]] = None) -> None:
        """
        Initialize the PII detector.
        
        Args:
            custom_patterns: Optional dictionary of custom regex patterns for PII detection
        """
        self._patterns: Dict[PIIType, List[Pattern]] = self._compile_patterns(custom_patterns)
    
    def _compile_patterns(self, custom_patterns: Optional[Dict[PIIType, List[str]]] = None) -> Dict[PIIType, List[Pattern]]:
        """
        Compile regex patterns for PII detection.
        
        Args:
            custom_patterns: Optional dictionary of custom regex patterns
            
        Returns:
            Dictionary of compiled regex patterns
        """
        patterns = {
            PIIType.EMAIL: [
                r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            ],
            PIIType.PHONE_NUMBER: [
                r'\b\+?1?[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b',
                r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b'
            ],
            PIIType.CREDIT_CARD: [
                r'\b(?:\d{4}[-\s]?){3}\d{4}\b',
                r'\b\d{13,16}\b'
            ],
            PIIType.SSN: [
                r'\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b'
            ],
            PIIType.IP_ADDRESS: [
                r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b',
                r'\b([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b'
            ],
            PIIType.DATE_OF_BIRTH: [
                r'\b(0[1-9]|1[0-2])[-/](0[1-9]|[12]\d|3[01])[-/](19|20)\d{2}\b',
                r'\b(19|20)\d{2}[-/](0[1-9]|1[0-2])[-/](0[1-9]|[12]\d|3[01])\b'
            ],
            PIIType.PASSPORT_NUMBER: [
                r'\b[A-Z]{1,2}\d{6,9}\b'
            ],
            PIIType.DRIVER_LICENSE: [
                r'\b[A-Z]\d{7}\b',
                r'\b[A-Z]{1,2}\d{5,7}\b'
            ],
            PIIType.NAME: [
                r'(?i)\b(?:mr|ms|mrs|dr|prof)\.\s+[a-z]+(?:\s+[a-z]+)?\b'
            ],
            PIIType.ADDRESS: [
                r'\b\d+\s+[A-Za-z0-9\s,]+(?:street|st|avenue|ave|road|rd|boulevard|blvd|lane|ln|drive|dr|way|parkway|pkwy|court|ct)\b',
                r'(?i)\b\d{5}(?:[-\s]\d{4})?\b'
            ]
        }
        
        if custom_patterns:
            for pii_type, pattern_list in custom_patterns.items():
                if pii_type in patterns:
                    patterns[pii_type].extend(pattern_list)
                else:
                    patterns[pii_type] = pattern_list
        
        compiled_patterns = {}
        for pii_type, pattern_list in patterns.items():
            compiled_patterns[pii_type] = [re.compile(pattern, re.IGNORECASE) for pattern in pattern_list]
        
        return compiled_patterns
    
    def detect(self, text: str) -> List[DetectionResult]:
        """
        Detect PII in the given text.
        
        Args:
            text: The text to analyze
            
        Returns:
            List of DetectionResult objects representing detected PII
        """
        results = []
        
        for pii_type, patterns in self._patterns.items():
            for pattern in patterns:
                for match in pattern.finditer(text):
                    start_pos, end_pos = match.span()
                    detected_text = match.group()
                    
                    confidence = 0.95
                    if pii_type in [PIIType.NAME, PIIType.ADDRESS]:
                        confidence = 0.85
                    
                    results.append(
                        DetectionResult(
                            text=detected_text,
                            start_pos=start_pos,
                            end_pos=end_pos,
                            detected_type=pii_type,
                            confidence=confidence
                        )
                    )
        
        results.sort(key=lambda x: x.start_pos)
        return results


class HarmfulContentDetector:
    """Class for detecting harmful content in text."""
    
    def __init__(self, offensive_words_file: Optional[str] = None) -> None:
        """
        Initialize the harmful content detector.
        
        Args:
            offensive_words_file: Optional path to a JSON file containing offensive words by category
        """
        self._offensive_words = self._load_offensive_words(offensive_words_file)
    
    def _load_offensive_words(self, file_path: Optional[str] = None) -> Dict[ContentFlag, Set[str]]:
        """
        Load offensive words from a file or use default ones.
        
        Args:
            file_path: Path to a JSON file containing offensive words
            
        Returns:
            Dictionary mapping content flags to sets of offensive words
        """
        default_words = {
            ContentFlag.PROFANITY: {
                "damn", "hell", "ass", "crap", "shit", "fuck", "bitch"
            },
            ContentFlag.HATE_SPEECH: {
                "slur", "racist", "bigot", "discrimination", "prejudice"
            },
            ContentFlag.VIOLENCE: {
                "kill", "murder", "attack", "hurt", "bomb", "shoot", "assault", "threat"
            },
            ContentFlag.SEXUAL_CONTENT: {
                "sex", "porn", "nude", "naked", "explicit"
            },
            ContentFlag.SELF_HARM: {
                "suicide", "self-harm", "cut myself", "kill myself", "end my life"
            },
            ContentFlag.PERSONAL_ATTACK: {
                "stupid", "idiot", "dumb", "moron", "loser", "worthless"
            },
            ContentFlag.MISINFORMATION: {
                "conspiracy", "hoax", "fake news", "propaganda"
            }
        }
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    loaded_words = json.load(f)
                
                result = {}
                for category, words in loaded_words.items():
                    try:
                        content_flag = ContentFlag(category.upper())
                        result[content_flag] = set(words)
                    except ValueError:
                        print(f"Warning: Unknown content flag '{category}', skipping.")
                
                return result
            except Exception as e:
                print(f"Error loading offensive words file: {e}")
                print("Using default offensive words instead.")
        
        return {flag: word_set for flag, word_set in default_words.items()}
    
    def detect(self, text: str) -> List[DetectionResult]:
        """
        Detect harmful content in the given text.
        
        Args:
            text: The text to analyze
            
        Returns:
            List of DetectionResult objects representing detected harmful content
        """
        results = []
        text_lower = text.lower()
        words = re.findall(r'\b\w+(?:[-\'’]\w+)*\b', text_lower)
        
        for flag, word_set in self._offensive_words.items():
            for word in word_set:
                for match in re.finditer(r'\b' + re.escape(word.lower()) + r'\b', text_lower):
                    start_pos, end_pos = match.span()
                    detected_text = text[start_pos:end_pos]
                    
                    results.append(
                        DetectionResult(
                            text=detected_text,
                            start_pos=start_pos,
                            end_pos=end_pos,
                            detected_type=flag,
                            confidence=0.9
                        )
                    )
        
        for flag, word_set in self._offensive_words.items():
            for word in word_set:
                if ' ' in word:
                    if word.lower() in text_lower:
                        start_pos = text_lower.find(word.lower())
                        end_pos = start_pos + len(word)
                        detected_text = text[start_pos:end_pos]
                        
                        results.append(
                            DetectionResult(
                                text=detected_text,
                                start_pos=start_pos,
                                end_pos=end_pos,
                                detected_type=flag,
                                confidence=0.9
                            )
                        )
        
        results.sort(key=lambda x: x.start_pos)
        return results


class GuardrailsService:
    """Main service class for implementing guardrails on LLM input and output."""
    
    def __init__(self, 
                 pii_detector: Optional[PIIDetector] = None,
                 content_detector: Optional[HarmfulContentDetector] = None,
                 redaction_char: str = "█",
                 log_file: Optional[str] = None) -> None:
        """
        Initialize the guardrails service.
        
        Args:
            pii_detector: Optional PII detector instance
            content_detector: Optional harmful content detector instance
            redaction_char: Character to use for redaction
            log_file: Optional file path for logging detections
        """
        self.pii_detector = pii_detector or PIIDetector()
        self.content_detector = content_detector or HarmfulContentDetector()
        self.redaction_char = redaction_char
        self.log_file = log_file
    
    def process_input(self, text: str) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Process user input text by detecting and redacting PII and harmful content.
        
        Args:
            text: User input text
            
        Returns:
            Tuple of (redacted_text, list of detections)
        """
        return self._process_text(text, is_input=True)
    
    def process_output(self, text: str) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Process LLM output text by detecting and redacting PII and harmful content.
        
        Args:
            text: LLM output text
            
        Returns:
            Tuple of (redacted_text, list of detections)
        """
        return self._process_text(text, is_input=False)
    
    def _process_text(self, text: str, is_input: bool) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Process text by detecting and redacting PII and harmful content.
        
        Args:
            text: The text to process
            is_input: Whether this is user input (True) or LLM output (False)
            
        Returns:
            Tuple of (redacted_text, list of detections)
        """
        pii_detections = self.pii_detector.detect(text)
        harmful_detections = self.content_detector.detect(text)
        
        all_detections = pii_detections + harmful_detections
        all_detections.sort(key=lambda x: x.start_pos)
        
        redacted_text = self._redact_text(text, all_detections)
        
        if self.log_file:
            self._log_detections(text, all_detections, is_input)
        
        detection_info = [detection.to_dict() for detection in all_detections]
        return redacted_text, detection_info
    
    def _redact_text(self, text: str, detections: List[DetectionResult]) -> str:
        """
        Redact detected sensitive information in the text.
        
        Args:
            text: Original text
            detections: List of detection results
            
        Returns:
            Text with sensitive information redacted
        """
        if not detections:
            return text
        
        result = ""
        last_end = 0
        
        for detection in detections:
            result += text[last_end:detection.start_pos]
            redacted_length = detection.end_pos - detection.start_pos
            result += self.redaction_char * redacted_length
            last_end = detection.end_pos
        
        result += text[last_end:]
        return result
    
    def _log_detections(self, text: str, detections: List[DetectionResult], is_input: bool) -> None:
        """
        Log detected sensitive information.
        
        Args:
            text: Original text
            detections: List of detection results
            is_input: Whether this is user input (True) or LLM output (False)
        """
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"Timestamp: {timestamp}\n")
                f.write(f"Type: {'User Input' if is_input else 'LLM Output'}\n")
                
                if detections:
                    f.write("Detections:\n")
                    for i, detection in enumerate(detections):
                        f.write(f"{i+1}. Type: {detection.detected_type.value}, ")
                        f.write(f"Text: '{detection.text}', ")
                        f.write(f"Position: ({detection.start_pos}, {detection.end_pos}), ")
                        f.write(f"Confidence: {detection.confidence:.2f}\n")
                else:
                    f.write("No detections\n")
                
                f.write("\n" + "-" * 50 + "\n\n")
        except Exception as e:
            print(f"Error logging detections: {e}")


def main() -> None:
    """Example usage of the guardrails service."""
    service = GuardrailsService(log_file="guardrails_log.txt")
    
    user_input = ("My name is John Smith and my email is john.smith@example.com. "
                 "My credit card number is 4111-1111-1111-1111. "
                 "This service is stupid and I hate it.")
    
    redacted_input, input_detections = service.process_input(user_input)
    
    print("Original user input:", user_input)
    print("Redacted user input:", redacted_input)
    print("Detections:", json.dumps(input_detections, indent=2))
    
    llm_output = ("Based on your information, John Smith, I can see that your email "
                 "is john.smith@example.com. Let me help you with your request.")
    
    redacted_output, output_detections = service.process_output(llm_output)
    
    print("\nOriginal LLM output:", llm_output)
    print("Redacted LLM output:", redacted_output)
    print("Detections:", json.dumps(output_detections, indent=2))


if __name__ == "__main__":
    main() 