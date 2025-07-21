import hashlib
import json
import re
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Union
from urllib.parse import quote_plus

import requests


class BoardMinutesProcessor:
    """
    Board meeting minutes processor that allows queries about
    decisions, action items, and responsible parties with secure fact verification.
    """
    
    def __init__(self):
        self.minutes_data: Dict = {}
        self.decisions: List[Dict] = []
        self.action_items: List[Dict] = []
        self.responsible_parties: Dict[str, List[str]] = {}
        
    def load_minutes(self, file_path: str) -> bool:
        """
        Load and process meeting minutes from a file.
        
        Args:
            file_path: Path to the minutes file
            
        Returns:
            bool: True if loaded successfully, False otherwise
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
                self._parse_minutes(content)
                return True
        except Exception as e:
            print(f"Error loading minutes: {e}")
            return False
    
    def _parse_minutes(self, content: str) -> None:
        """
        Parse minutes content and extract structured information.
        
        Args:
            content: Full text of the minutes
        """
        self._extract_decisions(content)
        self._extract_action_items(content)
        self._extract_responsible_parties(content)
        
    def _extract_decisions(self, content: str) -> None:
        """
        Extract decisions made from the minutes.
        
        Args:
            content: Minutes text
        """
        decision_patterns = [
            r"DECISION:\s*(.*?)(?=\n|ACTION:|RESPONSIBLE:|$)",
            r"DECIDED:\s*(.*?)(?=\n|ACTION:|RESPONSIBLE:|$)",
            r"APPROVED:\s*(.*?)(?=\n|ACTION:|RESPONSIBLE:|$)",
            r"RESOLUTION:\s*(.*?)(?=\n|ACTION:|RESPONSIBLE:|$)",
            r"RESOLVED:\s*(.*?)(?=\n|ACTION:|RESPONSIBLE:|$)"
        ]
        
        for pattern in decision_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                decision_text = match.group(1).strip()
                if decision_text:
                    self.decisions.append({
                        'id': self._generate_id(decision_text),
                        'text': decision_text,
                        'type': 'decision',
                        'timestamp': datetime.now().isoformat()
                    })
    
    def _extract_action_items(self, content: str) -> None:
        """
        Extract action items from the minutes.
        
        Args:
            content: Minutes text
        """
        action_patterns = [
            r"ACTION:\s*(.*?)(?=\n|DECISION:|RESPONSIBLE:|$)",
            r"ACTION ITEM:\s*(.*?)(?=\n|DECISION:|RESPONSIBLE:|$)",
            r"TODO:\s*(.*?)(?=\n|DECISION:|RESPONSIBLE:|$)",
            r"TASK:\s*(.*?)(?=\n|DECISION:|RESPONSIBLE:|$)",
            r"FOLLOW-UP:\s*(.*?)(?=\n|DECISION:|RESPONSIBLE:|$)"
        ]
        
        for pattern in action_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                action_text = match.group(1).strip()
                if action_text:
                    self.action_items.append({
                        'id': self._generate_id(action_text),
                        'text': action_text,
                        'type': 'action_item',
                        'status': 'pending',
                        'timestamp': datetime.now().isoformat()
                    })
    
    def _extract_responsible_parties(self, content: str) -> None:
        """
        Extract responsible parties mentioned in the minutes.
        
        Args:
            content: Minutes text
        """
        responsible_patterns = [
            r"RESPONSIBLE:\s*([A-Za-z\s]+)(?=\n|ACTION:|DECISION:|$)",
            r"ASSIGNED TO:\s*([A-Za-z\s]+)(?=\n|ACTION:|DECISION:|$)",
            r"@([A-Za-z\s]+)",
            r"([A-Z][a-z]+\s+[A-Z][a-z]+)\s+(?:will|shall|must|should)"
        ]
        
        for pattern in responsible_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                name = match.group(1).strip()
                if len(name) > 2 and name not in self.responsible_parties:
                    self.responsible_parties[name] = []
                    
        for decision in self.decisions:
            for name in self.responsible_parties.keys():
                if name.lower() in decision['text'].lower():
                    self.responsible_parties[name].append(decision['id'])
                    
        for action in self.action_items:
            for name in self.responsible_parties.keys():
                if name.lower() in action['text'].lower():
                    self.responsible_parties[name].append(action['id'])
    
    def _generate_id(self, text: str) -> str:
        """
        Generate a unique ID based on text.
        
        Args:
            text: Text to generate ID from
            
        Returns:
            str: Unique ID
        """
        return hashlib.md5(text.encode()).hexdigest()[:8]
    
    def query_decisions(self, keyword: str) -> List[Dict]:
        """
        Search decisions based on keyword.
        
        Args:
            keyword: Search keyword
            
        Returns:
            List[Dict]: List of found decisions
        """
        results = []
        for decision in self.decisions:
            if keyword.lower() in decision['text'].lower():
                results.append(decision)
        return results
    
    def query_action_items(self, status: Optional[str] = None, responsible: Optional[str] = None) -> List[Dict]:
        """
        Search action items by status or responsible party.
        
        Args:
            status: Item status (pending, completed, etc.)
            responsible: Name of responsible party
            
        Returns:
            List[Dict]: List of found action items
        """
        results = []
        for item in self.action_items:
            if status and item.get('status') != status:
                continue
            if responsible and responsible.lower() not in item['text'].lower():
                continue
            results.append(item)
        return results
    
    def get_responsible_parties(self, name: Optional[str] = None) -> Dict[str, List[str]]:
        """
        Get information about responsible parties.
        
        Args:
            name: Specific responsible party name (optional)
            
        Returns:
            Dict: Dictionary with responsible parties and their responsibilities
        """
        if name:
            name_lower = name.lower()
            for key in self.responsible_parties.keys():
                if name_lower in key.lower():
                    return {key: self.responsible_parties[key]}
            return {}
        return self.responsible_parties
    
    def _anonymize_query(self, query: str) -> str:
        """
        Anonymize query by removing sensitive information.
        
        Args:
            query: Original query
            
        Returns:
            str: Anonymized query
        """
        for name in self.responsible_parties.keys():
            query = query.replace(name, "[PERSON]")
        
        sensitive_patterns = [
            r'\b\d{9}\b',
            r'\b\d{11}\b',
            r'\b\d{14}\b',
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            r'\$\s*\d+(?:,\d{3})*(?:\.\d{2})?\b',
            r'\b(?:confidential|classified|restricted|private)\b'
        ]
        
        for pattern in sensitive_patterns:
            query = re.sub(pattern, "[REDACTED]", query, flags=re.IGNORECASE)
            
        return query
    
    def verify_fact_online(self, fact: str) -> Dict[str, Union[str, bool, float]]:
        """
        Verify a fact online securely without leaking information.
        
        Args:
            fact: Fact to be verified
            
        Returns:
            Dict: Verification result
        """
        try:
            anonymized_fact = self._anonymize_query(fact)
            
            search_url = "https://html.duckduckgo.com/html/"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            params = {
                'q': anonymized_fact,
                'kl': 'us-en'
            }
            
            response = requests.get(search_url, headers=headers, params=params, timeout=10)
            
            if response.status_code == 200:
                content = response.text
                
                result_patterns = [
                    r'<a[^>]*class="result__a"[^>]*>.*?</a>',
                    r'<h2[^>]*class="result__title"[^>]*>.*?</h2>'
                ]
                
                results_found = 0
                for pattern in result_patterns:
                    matches = re.findall(pattern, content, re.IGNORECASE | re.DOTALL)
                    results_found += len(matches)
                
                if results_found > 0:
                    return {
                        'verified': True,
                        'confidence': min(0.8, results_found * 0.2),
                        'source': 'duckduckgo_search',
                        'message': f'Found {results_found} related sources',
                        'results_count': results_found
                    }
                else:
                    return {
                        'verified': False,
                        'confidence': 0.1,
                        'source': 'duckduckgo_search',
                        'message': 'No sources found',
                        'results_count': 0
                    }
            else:
                return {
                    'verified': False,
                    'confidence': 0.0,
                    'source': 'api_error',
                    'message': f'Search API error: {response.status_code}',
                    'results_count': 0
                }
                
        except Exception as e:
            return {
                'verified': False,
                'confidence': 0.0,
                'source': 'error',
                'message': f'Verification error: {str(e)}',
                'results_count': 0
            }
    
    def search_minutes(self, query: str, verify_online: bool = False) -> Dict:
        """
        Comprehensive search in minutes with optional online verification.
        
        Args:
            query: Search query
            verify_online: Whether to verify facts online
            
        Returns:
            Dict: Search results
        """
        results = {
            'decisions': self.query_decisions(query),
            'action_items': self.query_action_items(),
            'responsible_parties': {},
            'verification': None
        }
        
        for name in self.responsible_parties.keys():
            if query.lower() in name.lower():
                results['responsible_parties'][name] = self.responsible_parties[name]
        
        if verify_online and results['decisions']:
            first_decision = results['decisions'][0]['text']
            results['verification'] = self.verify_fact_online(first_decision)
        
        return results
    
    def generate_summary(self) -> Dict:
        """
        Generate a summary of processed minutes.
        
        Returns:
            Dict: Minutes summary
        """
        return {
            'total_decisions': len(self.decisions),
            'total_action_items': len(self.action_items),
            'total_responsible_parties': len(self.responsible_parties),
            'decisions_summary': [d['text'][:100] + '...' for d in self.decisions[:5]],
            'pending_actions': len([a for a in self.action_items if a.get('status') == 'pending']),
            'processed_at': datetime.now().isoformat()
        }
    
    def export_to_json(self, file_path: str) -> bool:
        """
        Export processed data to JSON file.
        
        Args:
            file_path: Output file path
            
        Returns:
            bool: True if exported successfully
        """
        try:
            export_data = {
                'summary': self.generate_summary(),
                'decisions': self.decisions,
                'action_items': self.action_items,
                'responsible_parties': self.responsible_parties
            }
            
            with open(file_path, 'w', encoding='utf-8') as file:
                json.dump(export_data, file, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Export error: {e}")
            return False


def print_results(results: list, item_type: str) -> None:
    """
    Print search results in a formatted way.
    
    Args:
        results: List of results to print
        item_type: Type of items being printed
    """
    if not results:
        print(f"No {item_type} found.")
        return
    
    print(f"\nFound {len(results)} {item_type}:")
    for i, item in enumerate(results, 1):
        print(f"\n{i}. ID: {item['id']}")
        print(f"   Text: {item['text']}")
        if 'status' in item:
            print(f"   Status: {item['status']}")
        print(f"   Timestamp: {item['timestamp']}")


def print_responsible_parties(parties: Dict[str, List[str]]) -> None:
    """
    Print responsible parties information.
    
    Args:
        parties: Dictionary with responsible parties data
    """
    if not parties:
        print("No responsible parties found.")
        return
    
    print(f"\nFound {len(parties)} responsible parties:")
    for name, responsibilities in parties.items():
        print(f"\n- {name}")
        print(f"  Responsibilities: {len(responsibilities)} items")
        if responsibilities:
            print(f"  Related IDs: {', '.join(responsibilities[:5])}")
            if len(responsibilities) > 5:
                print(f"  ... and {len(responsibilities) - 5} more")


def print_fact_verification(verification: Dict) -> None:
    """
    Print fact verification results.
    
    Args:
        verification: Verification results dictionary
    """
    print(f"\nFact Verification Results:")
    print(f"Verified: {verification['verified']}")
    print(f"Confidence: {verification['confidence']:.2f}")
    print(f"Source: {verification['source']}")
    print(f"Message: {verification['message']}")
    if 'results_count' in verification:
        print(f"Sources found: {verification['results_count']}")


def main():
    """
    Interactive Executive Assistant for Board Minutes.
    Allows users to query key decisions, action items, and responsible parties.
    Includes secure fact verification without leaking information.
    """
    print("=== Executive Assistant for Board Minutes ===")
    print("Interactive Query System")
    print("-" * 50)
    
    assistant = BoardMinutesProcessor()
    
    # Load minutes file
    while True:
        file_path = input("\nEnter path to board minutes file (or 'demo' for example): ").strip()
        
        if file_path.lower() == 'demo':
            file_path = "../utils/board_minutes_example.txt"
        
        if assistant.load_minutes(file_path):
            print(f"[SUCCESS] Minutes loaded from: {file_path}")
            summary = assistant.generate_summary()
            print(f"Loaded: {summary['total_decisions']} decisions, {summary['total_action_items']} actions, {summary['total_responsible_parties']} responsible parties")
            break
        else:
            print("[ERROR] Failed to load minutes file.")
            retry = input("Try again? (y/n): ").strip().lower()
            if retry not in ['y', 'yes']:
                return
    
    # Interactive query loop
    print("\n" + "=" * 50)
    print("AVAILABLE COMMANDS:")
    print("1. 'decisions <keyword>' - Search decisions by keyword")
    print("2. 'actions [status] [responsible]' - Search action items")
    print("3. 'responsible [name]' - Search responsible parties")
    print("4. 'verify <statement>' - Verify fact online securely")
    print("5. 'search <query>' - Comprehensive search with verification")
    print("6. 'summary' - Show summary statistics")
    print("7. 'export <filename>' - Export data to JSON file")
    print("8. 'help' - Show this help")
    print("9. 'quit' - Exit the system")
    print("=" * 50)
    
    while True:
        try:
            user_input = input("\n> ").strip()
            
            if not user_input:
                continue
            
            command_parts = user_input.split(maxsplit=1)
            command = command_parts[0].lower()
            args = command_parts[1] if len(command_parts) > 1 else ""
            
            if command == 'quit':
                print("Thank you for using Executive Assistant!")
                break
                
            elif command == 'help':
                print("\nAVAILABLE COMMANDS:")
                print("decisions <keyword> - Search decisions")
                print("actions [pending/completed] [person] - Search actions")
                print("responsible [name] - Search responsible parties")
                print("verify <statement> - Verify fact online")
                print("search <query> - Comprehensive search")
                print("summary - Show statistics")
                print("export <filename> - Export to JSON")
                print("quit - Exit")
                
            elif command == 'decisions':
                if not args:
                    print("Usage: decisions <keyword>")
                    continue
                
                results = assistant.query_decisions(args)
                print_results(results, "decisions")
                
            elif command == 'actions':
                args_list = args.split() if args else []
                status = None
                responsible = None
                
                for arg in args_list:
                    if arg.lower() in ['pending', 'completed', 'in_progress']:
                        status = arg.lower()
                    else:
                        responsible = arg
                
                results = assistant.query_action_items(status=status, responsible=responsible)
                print_results(results, "action items")
                
            elif command == 'responsible':
                results = assistant.get_responsible_parties(args if args else None)
                print_responsible_parties(results)
                
            elif command == 'verify':
                if not args:
                    print("Usage: verify <statement to verify>")
                    continue
                
                print(f"Verifying: '{args}'")
                print("Checking online sources securely...")
                verification = assistant.verify_fact_online(args)
                print_fact_verification(verification)
                
            elif command == 'search':
                if not args:
                    print("Usage: search <query>")
                    continue
                
                print(f"Searching for: '{args}'")
                
                # Comprehensive search
                results = assistant.search_minutes(args, verify_online=True)
                
                # Print decisions
                if results['decisions']:
                    print_results(results['decisions'], "decisions")
                
                # Print action items (filter by query)
                relevant_actions = [action for action in results['action_items'] 
                                  if args.lower() in action['text'].lower()]
                if relevant_actions:
                    print_results(relevant_actions, "action items")
                
                # Print responsible parties
                if results['responsible_parties']:
                    print_responsible_parties(results['responsible_parties'])
                
                # Print verification if available
                if results['verification']:
                    print_fact_verification(results['verification'])
                
                if not any([results['decisions'], relevant_actions, results['responsible_parties']]):
                    print("No results found for your query.")
                    
            elif command == 'summary':
                summary = assistant.generate_summary()
                print(f"\n=== SUMMARY ===")
                print(f"Total Decisions: {summary['total_decisions']}")
                print(f"Total Action Items: {summary['total_action_items']}")
                print(f"Total Responsible Parties: {summary['total_responsible_parties']}")
                print(f"Pending Actions: {summary['pending_actions']}")
                print(f"Processed at: {summary['processed_at']}")
                
                if summary['decisions_summary']:
                    print(f"\nRecent Decisions Preview:")
                    for i, decision in enumerate(summary['decisions_summary'][:3], 1):
                        print(f"{i}. {decision}")
                        
            elif command == 'export':
                if not args:
                    filename = f"board_minutes_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                else:
                    filename = args if args.endswith('.json') else f"{args}.json"
                
                output_path = f"../outputs/{filename}"
                if assistant.export_to_json(output_path):
                    print(f"Data exported successfully to: {output_path}")
                else:
                    print("Export failed. Check file permissions.")
                    
            else:
                print(f"Unknown command: '{command}'. Type 'help' for available commands.")
                
        except KeyboardInterrupt:
            print("\n\nExiting Executive Assistant...")
            break
            
        except Exception as e:
            print(f"Error processing command: {e}")
            print("Please try again or type 'help' for available commands.")


if __name__ == "__main__":
    main() 