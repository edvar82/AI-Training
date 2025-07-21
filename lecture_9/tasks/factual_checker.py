import difflib
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union

import requests


class FactualChecker:
    """
    Factual information checker that verifies information against multiple documents
    and online sources to prevent hallucinations and ensure accuracy.
    """
    
    def __init__(self):
        self.documents: Dict[str, Dict] = {}
        self.facts_database: List[Dict] = []
        self.verification_cache: Dict[str, Dict] = {}
        self.consistency_threshold: float = 0.7
        
    def load_document(self, file_path: str, document_type: str = "text") -> bool:
        """
        Load and process a document for fact checking.
        
        Args:
            file_path: Path to the document
            document_type: Type of document (text, json, etc.)
            
        Returns:
            bool: True if loaded successfully
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
                
            document_id = self._generate_document_id(file_path)
            
            self.documents[document_id] = {
                'path': file_path,
                'type': document_type,
                'content': content,
                'facts': self._extract_facts(content),
                'loaded_at': datetime.now().isoformat(),
                'word_count': len(content.split())
            }
            
            self._update_facts_database(document_id)
            return True
            
        except Exception as e:
            print(f"Error loading document: {e}")
            return False
    
    def load_multiple_documents(self, file_paths: List[str]) -> Dict[str, bool]:
        """
        Load multiple documents for cross-reference checking.
        
        Args:
            file_paths: List of document paths
            
        Returns:
            Dict: Results of loading each document
        """
        results = {}
        for file_path in file_paths:
            results[file_path] = self.load_document(file_path)
        return results
    
    def _generate_document_id(self, file_path: str) -> str:
        """
        Generate unique document ID.
        
        Args:
            file_path: Path to document
            
        Returns:
            str: Unique document ID
        """
        return hashlib.md5(file_path.encode()).hexdigest()[:8]
    
    def _extract_facts(self, content: str) -> List[Dict]:
        """
        Extract factual statements from document content.
        
        Args:
            content: Document content
            
        Returns:
            List[Dict]: Extracted facts
        """
        facts = []
        
        # Extract numerical facts
        number_patterns = [
            r'(\d+(?:,\d{3})*(?:\.\d+)?)\s*(?:percent|%|dollars?|\$|million|billion|thousand)',
            r'in\s+(\d{4})\s*[,.]',  # Years
            r'(\d+(?:,\d{3})*)\s+(?:people|users|customers|employees)',
            r'(?:increased|decreased|grew|fell)\s+by\s+(\d+(?:\.\d+)?)\s*(?:percent|%)'
        ]
        
        for pattern in number_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                fact = {
                    'id': hashlib.md5(match.group(0).encode()).hexdigest()[:8],
                    'type': 'numerical',
                    'statement': match.group(0).strip(),
                    'value': match.group(1),
                    'context': self._get_context(content, match.start(), match.end()),
                    'confidence': 0.8
                }
                facts.append(fact)
        
        # Extract named entities and statements
        entity_patterns = [
            r'([A-Z][a-z]+\s+[A-Z][a-z]+)\s+(?:is|was|will be|became)\s+([^.]+)',
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:announced|reported|stated|confirmed)\s+([^.]+)',
            r'The\s+([^,]+),\s+([^,]+),\s+([^.]+)'
        ]
        
        for pattern in entity_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                fact = {
                    'id': hashlib.md5(match.group(0).encode()).hexdigest()[:8],
                    'type': 'statement',
                    'statement': match.group(0).strip(),
                    'entity': match.group(1).strip(),
                    'claim': match.group(2).strip() if len(match.groups()) > 1 else "",
                    'context': self._get_context(content, match.start(), match.end()),
                    'confidence': 0.6
                }
                facts.append(fact)
        
        return facts
    
    def _get_context(self, content: str, start: int, end: int, window: int = 100) -> str:
        """
        Get context around a fact for better understanding.
        
        Args:
            content: Full content
            start: Start position of fact
            end: End position of fact
            window: Context window size
            
        Returns:
            str: Context around the fact
        """
        context_start = max(0, start - window)
        context_end = min(len(content), end + window)
        return content[context_start:context_end].strip()
    
    def _update_facts_database(self, document_id: str) -> None:
        """
        Update the central facts database with facts from a document.
        
        Args:
            document_id: ID of the document
        """
        document = self.documents[document_id]
        for fact in document['facts']:
            fact['source_document'] = document_id
            fact['source_path'] = document['path']
            self.facts_database.append(fact)
    
    def check_consistency_across_documents(self) -> Dict[str, List[Dict]]:
        """
        Check consistency of facts across multiple documents.
        
        Returns:
            Dict: Consistency analysis results
        """
        consistency_results = {
            'consistent_facts': [],
            'inconsistent_facts': [],
            'unique_facts': [],
            'confidence_score': 0.0
        }
        
        # Group facts by similarity
        fact_groups = self._group_similar_facts()
        
        for group in fact_groups:
            if len(group) == 1:
                consistency_results['unique_facts'].append(group[0])
            elif self._are_facts_consistent(group):
                consistency_results['consistent_facts'].append({
                    'facts': group,
                    'agreement_level': self._calculate_agreement_level(group)
                })
            else:
                consistency_results['inconsistent_facts'].append({
                    'facts': group,
                    'conflicts': self._identify_conflicts(group)
                })
        
        # Calculate overall confidence
        total_facts = len(self.facts_database)
        consistent_count = len(consistency_results['consistent_facts'])
        consistency_results['confidence_score'] = consistent_count / total_facts if total_facts > 0 else 0.0
        
        return consistency_results
    
    def _group_similar_facts(self) -> List[List[Dict]]:
        """
        Group similar facts for comparison.
        
        Returns:
            List[List[Dict]]: Groups of similar facts
        """
        groups = []
        processed_facts = set()
        
        for i, fact1 in enumerate(self.facts_database):
            if fact1['id'] in processed_facts:
                continue
                
            group = [fact1]
            processed_facts.add(fact1['id'])
            
            for j, fact2 in enumerate(self.facts_database[i+1:], i+1):
                if fact2['id'] in processed_facts:
                    continue
                    
                if self._are_facts_similar(fact1, fact2):
                    group.append(fact2)
                    processed_facts.add(fact2['id'])
            
            groups.append(group)
        
        return groups
    
    def _are_facts_similar(self, fact1: Dict, fact2: Dict) -> bool:
        """
        Check if two facts are similar enough to compare.
        
        Args:
            fact1: First fact
            fact2: Second fact
            
        Returns:
            bool: True if facts are similar
        """
        # Compare by type first
        if fact1['type'] != fact2['type']:
            return False
        
        # For numerical facts, compare context
        if fact1['type'] == 'numerical':
            similarity = difflib.SequenceMatcher(
                None, 
                fact1['context'].lower(), 
                fact2['context'].lower()
            ).ratio()
            return similarity > 0.6
        
        # For statements, compare entity and claim
        if fact1['type'] == 'statement':
            entity_match = fact1.get('entity', '').lower() == fact2.get('entity', '').lower()
            claim_similarity = difflib.SequenceMatcher(
                None,
                fact1.get('claim', '').lower(),
                fact2.get('claim', '').lower()
            ).ratio()
            return entity_match or claim_similarity > 0.7
        
        return False
    
    def _are_facts_consistent(self, facts: List[Dict]) -> bool:
        """
        Check if a group of facts is consistent.
        
        Args:
            facts: List of facts to check
            
        Returns:
            bool: True if facts are consistent
        """
        if len(facts) < 2:
            return True
        
        # For numerical facts, check if values are close
        if facts[0]['type'] == 'numerical':
            values = []
            for fact in facts:
                try:
                    value = float(fact['value'].replace(',', ''))
                    values.append(value)
                except ValueError:
                    continue
            
            if len(values) < 2:
                return True
            
            max_val = max(values)
            min_val = min(values)
            
            # Allow 10% variance
            return (max_val - min_val) / max_val <= 0.1 if max_val > 0 else True
        
        # For statements, check claim consistency
        if facts[0]['type'] == 'statement':
            claims = [fact.get('claim', '').lower() for fact in facts]
            unique_claims = set(claims)
            return len(unique_claims) <= 2  # Allow some variation in wording
        
        return True
    
    def _calculate_agreement_level(self, facts: List[Dict]) -> float:
        """
        Calculate agreement level among similar facts.
        
        Args:
            facts: List of facts
            
        Returns:
            float: Agreement level (0.0 to 1.0)
        """
        if len(facts) < 2:
            return 1.0
        
        total_confidence = sum(fact['confidence'] for fact in facts)
        return min(1.0, total_confidence / len(facts))
    
    def _identify_conflicts(self, facts: List[Dict]) -> List[str]:
        """
        Identify specific conflicts in a group of facts.
        
        Args:
            facts: List of conflicting facts
            
        Returns:
            List[str]: List of identified conflicts
        """
        conflicts = []
        
        if facts[0]['type'] == 'numerical':
            values = []
            for fact in facts:
                try:
                    value = float(fact['value'].replace(',', ''))
                    values.append((value, fact['source_path']))
                except ValueError:
                    continue
            
            if len(values) > 1:
                conflicts.append(f"Numerical conflict: values range from {min(v[0] for v in values)} to {max(v[0] for v in values)}")
        
        elif facts[0]['type'] == 'statement':
            claims = [(fact.get('claim', ''), fact['source_path']) for fact in facts]
            unique_claims = list(set(claim[0] for claim in claims))
            if len(unique_claims) > 1:
                conflicts.append(f"Statement conflict: {len(unique_claims)} different claims found")
        
        return conflicts
    
    def verify_fact_online(self, fact: str, context: str = "") -> Dict[str, Union[str, bool, float]]:
        """
        Verify a fact online securely without leaking information.
        
        Args:
            fact: Fact to verify
            context: Additional context
            
        Returns:
            Dict: Verification result
        """
        # Check cache first
        cache_key = hashlib.md5(f"{fact}{context}".encode()).hexdigest()
        if cache_key in self.verification_cache:
            return self.verification_cache[cache_key]
        
        try:
            # Anonymize the query
            anonymized_fact = self._anonymize_query(f"{fact} {context}".strip())
            
            search_url = "https://html.duckduckgo.com/html/"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            params = {
                'q': anonymized_fact,
                'kl': 'us-en'
            }
            
            response = requests.get(search_url, headers=headers, params=params, timeout=15)
            
            if response.status_code == 200:
                content = response.text
                
                # Count search results
                result_patterns = [
                    r'<a[^>]*class="result__a"[^>]*>.*?</a>',
                    r'<h2[^>]*class="result__title"[^>]*>.*?</h2>',
                    r'<div[^>]*class="result__snippet"[^>]*>.*?</div>'
                ]
                
                results_found = 0
                for pattern in result_patterns:
                    matches = re.findall(pattern, content, re.IGNORECASE | re.DOTALL)
                    results_found += len(matches)
                
                # Analyze content for verification keywords
                verification_keywords = self._extract_verification_keywords(anonymized_fact)
                keyword_matches = 0
                
                for keyword in verification_keywords:
                    if keyword.lower() in content.lower():
                        keyword_matches += 1
                
                confidence = min(0.9, (results_found * 0.1) + (keyword_matches * 0.2))
                
                result = {
                    'verified': results_found > 0,
                    'confidence': confidence,
                    'source': 'duckduckgo_search',
                    'message': f'Found {results_found} related sources, {keyword_matches} keyword matches',
                    'results_count': results_found,
                    'keyword_matches': keyword_matches
                }
                
                # Cache the result
                self.verification_cache[cache_key] = result
                return result
                
            else:
                result = {
                    'verified': False,
                    'confidence': 0.0,
                    'source': 'api_error',
                    'message': f'Search API error: {response.status_code}',
                    'results_count': 0
                }
                return result
                
        except Exception as e:
            result = {
                'verified': False,
                'confidence': 0.0,
                'source': 'error',
                'message': f'Verification error: {str(e)}',
                'results_count': 0
            }
            return result
    
    def _anonymize_query(self, query: str) -> str:
        """
        Anonymize query by removing sensitive information.
        
        Args:
            query: Original query
            
        Returns:
            str: Anonymized query
        """
        # Remove specific names and sensitive patterns
        sensitive_patterns = [
            r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b',  # Names
            r'\b\d{9,}\b',  # Long numbers
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Emails
            r'\$\s*\d+(?:,\d{3})*(?:\.\d{2})?\b',  # Specific amounts
            r'\b(?:confidential|internal|proprietary|classified)\b'  # Sensitive keywords
        ]
        
        anonymized = query
        for pattern in sensitive_patterns:
            anonymized = re.sub(pattern, "[REDACTED]", anonymized, flags=re.IGNORECASE)
        
        return anonymized.strip()
    
    def _extract_verification_keywords(self, fact: str) -> List[str]:
        """
        Extract keywords from fact for verification.
        
        Args:
            fact: Fact to extract keywords from
            
        Returns:
            List[str]: List of keywords
        """
        # Remove common words and extract meaningful terms
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'was', 'are', 'were', 'will', 'would', 'could', 'should'}
        
        words = re.findall(r'\b[a-zA-Z]{3,}\b', fact.lower())
        keywords = [word for word in words if word not in stop_words]
        
        return keywords[:5]  # Return top 5 keywords
    
    def comprehensive_fact_check(self, statement: str) -> Dict:
        """
        Perform comprehensive fact checking against documents and online sources.
        
        Args:
            statement: Statement to fact-check
            
        Returns:
            Dict: Comprehensive fact-check results
        """
        results = {
            'statement': statement,
            'document_verification': self._check_against_documents(statement),
            'online_verification': self.verify_fact_online(statement),
            'consistency_check': self._check_internal_consistency(statement),
            'final_verdict': 'unknown',
            'confidence_score': 0.0,
            'recommendations': []
        }
        
        # Calculate final verdict
        doc_score = results['document_verification']['confidence']
        online_score = results['online_verification']['confidence']
        consistency_score = results['consistency_check']['confidence']
        
        final_confidence = (doc_score * 0.4) + (online_score * 0.4) + (consistency_score * 0.2)
        results['confidence_score'] = final_confidence
        
        if final_confidence >= 0.8:
            results['final_verdict'] = 'verified'
        elif final_confidence >= 0.6:
            results['final_verdict'] = 'likely_true'
        elif final_confidence >= 0.4:
            results['final_verdict'] = 'uncertain'
        elif final_confidence >= 0.2:
            results['final_verdict'] = 'likely_false'
        else:
            results['final_verdict'] = 'false'
        
        # Generate recommendations
        if final_confidence < 0.6:
            results['recommendations'].append("Requires additional verification")
        if doc_score < 0.5:
            results['recommendations'].append("Not well supported by loaded documents")
        if online_score < 0.5:
            results['recommendations'].append("Limited online evidence found")
        if consistency_score < 0.5:
            results['recommendations'].append("Potential consistency issues detected")
        
        return results
    
    def _check_against_documents(self, statement: str) -> Dict:
        """
        Check statement against loaded documents.
        
        Args:
            statement: Statement to check
            
        Returns:
            Dict: Document verification results
        """
        if not self.facts_database:
            return {
                'verified': False,
                'confidence': 0.0,
                'message': 'No documents loaded',
                'supporting_facts': []
            }
        
        supporting_facts = []
        statement_lower = statement.lower()
        
        for fact in self.facts_database:
            fact_text = fact['statement'].lower()
            similarity = difflib.SequenceMatcher(None, statement_lower, fact_text).ratio()
            
            if similarity > 0.6:
                supporting_facts.append({
                    'fact': fact,
                    'similarity': similarity,
                    'source': fact['source_path']
                })
        
        if supporting_facts:
            avg_confidence = sum(sf['similarity'] * sf['fact']['confidence'] for sf in supporting_facts) / len(supporting_facts)
            return {
                'verified': True,
                'confidence': min(1.0, avg_confidence),
                'message': f'Found {len(supporting_facts)} supporting facts',
                'supporting_facts': supporting_facts[:3]  # Top 3
            }
        else:
            return {
                'verified': False,
                'confidence': 0.0,
                'message': 'No supporting facts found in documents',
                'supporting_facts': []
            }
    
    def _check_internal_consistency(self, statement: str) -> Dict:
        """
        Check statement for internal consistency.
        
        Args:
            statement: Statement to check
            
        Returns:
            Dict: Consistency check results
        """
        # Basic consistency checks
        inconsistency_patterns = [
            r'(\d+)\s*percent.*?(\d+)\s*percent',  # Multiple percentages
            r'(increased|grew).*?(decreased|fell)',  # Contradictory trends
            r'(always|never).*?(sometimes|often)',  # Absolute vs relative
            r'(all|every).*?(some|few)',  # Universal vs particular
        ]
        
        inconsistencies = []
        for pattern in inconsistency_patterns:
            matches = re.finditer(pattern, statement, re.IGNORECASE)
            for match in matches:
                inconsistencies.append(f"Potential contradiction: {match.group(0)}")
        
        confidence = 1.0 - (len(inconsistencies) * 0.3)
        confidence = max(0.0, confidence)
        
        return {
            'consistent': len(inconsistencies) == 0,
            'confidence': confidence,
            'inconsistencies': inconsistencies,
            'message': f'Found {len(inconsistencies)} potential inconsistencies'
        }
    
    def generate_fact_report(self) -> Dict:
        """
        Generate comprehensive report of all loaded facts and their verification status.
        
        Returns:
            Dict: Comprehensive fact report
        """
        if not self.documents:
            return {'error': 'No documents loaded'}
        
        consistency_analysis = self.check_consistency_across_documents()
        
        report = {
            'summary': {
                'total_documents': len(self.documents),
                'total_facts': len(self.facts_database),
                'consistent_facts': len(consistency_analysis['consistent_facts']),
                'inconsistent_facts': len(consistency_analysis['inconsistent_facts']),
                'unique_facts': len(consistency_analysis['unique_facts']),
                'overall_confidence': consistency_analysis['confidence_score'],
                'generated_at': datetime.now().isoformat()
            },
            'document_analysis': {},
            'consistency_analysis': consistency_analysis,
            'recommendations': []
        }
        
        # Analyze each document
        for doc_id, document in self.documents.items():
            report['document_analysis'][doc_id] = {
                'path': document['path'],
                'facts_count': len(document['facts']),
                'word_count': document['word_count'],
                'fact_density': len(document['facts']) / document['word_count'] if document['word_count'] > 0 else 0,
                'avg_fact_confidence': sum(f['confidence'] for f in document['facts']) / len(document['facts']) if document['facts'] else 0
            }
        
        # Generate recommendations
        if report['summary']['overall_confidence'] < 0.7:
            report['recommendations'].append("Consider additional document sources for better verification")
        
        if len(consistency_analysis['inconsistent_facts']) > 0:
            report['recommendations'].append("Review inconsistent facts and resolve conflicts")
        
        if report['summary']['total_facts'] < 10:
            report['recommendations'].append("Load more documents to improve fact-checking accuracy")
        
        return report
    
    def export_results(self, file_path: str) -> bool:
        """
        Export fact-checking results to JSON file.
        
        Args:
            file_path: Output file path
            
        Returns:
            bool: True if exported successfully
        """
        try:
            report = self.generate_fact_report()
            report['verification_cache'] = self.verification_cache
            
            with open(file_path, 'w', encoding='utf-8') as file:
                json.dump(report, file, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Export error: {e}")
            return False


def main():
    """
    Interactive Factual Information Checker.
    Verifies information against documents and online sources to prevent hallucinations.
    """
    print("=== Factual Information Checker ===")
    print("Prevent hallucinations through document and online verification")
    print("-" * 60)
    
    checker = FactualChecker()
    
    # Load documents
    print("\nDocument Loading Phase:")
    while True:
        action = input("Enter 'file <path>' to load document, 'demo' for examples, or 'done' to continue: ").strip()
        
        if action.lower() == 'done':
            if not checker.documents:
                print("Warning: No documents loaded. Fact-checking will rely only on online verification.")
            break
        elif action.lower() == 'demo':
            # Load demo documents
            demo_paths = ["../utils/board_minutes_example.txt"]
            results = checker.load_multiple_documents(demo_paths)
            for path, success in results.items():
                status = "[SUCCESS]" if success else "[FAILED]"
                print(f"{status} {path}")
        elif action.startswith('file '):
            file_path = action[5:].strip()
            if checker.load_document(file_path):
                print(f"[SUCCESS] Loaded: {file_path}")
            else:
                print(f"[FAILED] Could not load: {file_path}")
        else:
            print("Invalid command. Use 'file <path>', 'demo', or 'done'")
    
    if checker.documents:
        print(f"\nLoaded {len(checker.documents)} documents with {len(checker.facts_database)} facts")
        
        # Show consistency analysis
        consistency = checker.check_consistency_across_documents()
        print(f"Consistency Score: {consistency['confidence_score']:.2f}")
        print(f"Consistent Facts: {len(consistency['consistent_facts'])}")
        print(f"Inconsistent Facts: {len(consistency['inconsistent_facts'])}")
    
    # Interactive fact checking
    print("\n" + "=" * 60)
    print("AVAILABLE COMMANDS:")
    print("1. 'check <statement>' - Comprehensive fact check")
    print("2. 'verify <statement>' - Online verification only")
    print("3. 'consistency' - Show document consistency analysis")
    print("4. 'report' - Generate comprehensive report")
    print("5. 'export <filename>' - Export results to JSON")
    print("6. 'help' - Show this help")
    print("7. 'quit' - Exit the system")
    print("=" * 60)
    
    while True:
        try:
            user_input = input("\n> ").strip()
            
            if not user_input:
                continue
            
            command_parts = user_input.split(maxsplit=1)
            command = command_parts[0].lower()
            args = command_parts[1] if len(command_parts) > 1 else ""
            
            if command == 'quit':
                print("Thank you for using Factual Information Checker!")
                break
                
            elif command == 'help':
                print("\nAVAILABLE COMMANDS:")
                print("check <statement> - Full fact verification")
                print("verify <statement> - Online verification only")
                print("consistency - Document consistency analysis")
                print("report - Generate comprehensive report")
                print("export <filename> - Export to JSON")
                print("quit - Exit")
                
            elif command == 'check':
                if not args:
                    print("Usage: check <statement to verify>")
                    continue
                
                print(f"Fact-checking: '{args}'")
                print("Analyzing against documents and online sources...")
                
                results = checker.comprehensive_fact_check(args)
                
                print(f"\nFACT-CHECK RESULTS:")
                print(f"Statement: {results['statement']}")
                print(f"Final Verdict: {results['final_verdict'].replace('_', ' ').title()}")
                print(f"Confidence Score: {results['confidence_score']:.2f}")
                
                print(f"\nDocument Verification:")
                doc_ver = results['document_verification']
                print(f"  Verified: {doc_ver['verified']}")
                print(f"  Confidence: {doc_ver['confidence']:.2f}")
                print(f"  Message: {doc_ver['message']}")
                
                print(f"\nOnline Verification:")
                online_ver = results['online_verification']
                print(f"  Verified: {online_ver['verified']}")
                print(f"  Confidence: {online_ver['confidence']:.2f}")
                print(f"  Sources found: {online_ver.get('results_count', 0)}")
                
                if results['recommendations']:
                    print(f"\nRecommendations:")
                    for rec in results['recommendations']:
                        print(f"  - {rec}")
                        
            elif command == 'verify':
                if not args:
                    print("Usage: verify <statement to verify online>")
                    continue
                
                print(f"Online verification: '{args}'")
                print("Checking external sources securely...")
                
                verification = checker.verify_fact_online(args)
                
                print(f"\nONLINE VERIFICATION RESULTS:")
                print(f"Verified: {verification['verified']}")
                print(f"Confidence: {verification['confidence']:.2f}")
                print(f"Source: {verification['source']}")
                print(f"Message: {verification['message']}")
                
            elif command == 'consistency':
                if not checker.documents:
                    print("No documents loaded for consistency analysis")
                    continue
                
                consistency = checker.check_consistency_across_documents()
                
                print(f"\nCONSISTENCY ANALYSIS:")
                print(f"Overall Confidence: {consistency['confidence_score']:.2f}")
                print(f"Consistent Facts: {len(consistency['consistent_facts'])}")
                print(f"Inconsistent Facts: {len(consistency['inconsistent_facts'])}")
                print(f"Unique Facts: {len(consistency['unique_facts'])}")
                
                if consistency['inconsistent_facts']:
                    print(f"\nInconsistencies found:")
                    for i, conflict in enumerate(consistency['inconsistent_facts'][:3], 1):
                        print(f"  {i}. {len(conflict['facts'])} conflicting facts")
                        for conf in conflict['conflicts'][:2]:
                            print(f"     - {conf}")
                            
            elif command == 'report':
                print("Generating comprehensive fact report...")
                
                report = checker.generate_fact_report()
                
                if 'error' in report:
                    print(f"Error: {report['error']}")
                    continue
                
                summary = report['summary']
                print(f"\nFACT-CHECKING REPORT:")
                print(f"Total Documents: {summary['total_documents']}")
                print(f"Total Facts: {summary['total_facts']}")
                print(f"Consistent Facts: {summary['consistent_facts']}")
                print(f"Inconsistent Facts: {summary['inconsistent_facts']}")
                print(f"Overall Confidence: {summary['overall_confidence']:.2f}")
                
                if report['recommendations']:
                    print(f"\nRecommendations:")
                    for rec in report['recommendations']:
                        print(f"  - {rec}")
                        
            elif command == 'export':
                if not args:
                    filename = f"fact_check_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                else:
                    filename = args if args.endswith('.json') else f"{args}.json"
                
                output_path = f"../outputs/{filename}"
                if checker.export_results(output_path):
                    print(f"Results exported successfully to: {output_path}")
                else:
                    print("Export failed. Check file permissions.")
                    
            else:
                print(f"Unknown command: '{command}'. Type 'help' for available commands.")
                
        except KeyboardInterrupt:
            print("\n\nExiting Factual Information Checker...")
            break
            
        except Exception as e:
            print(f"Error processing command: {e}")
            print("Please try again or type 'help' for available commands.")


if __name__ == "__main__":
    main() 