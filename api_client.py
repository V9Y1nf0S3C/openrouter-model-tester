import json
import requests
from typing import Dict, List, Tuple, Optional
from decimal import Decimal
import urllib3

# Suppress SSL warnings when using proxy without verification
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class OpenRouterClient:
    """Client for OpenRouter API interactions with proxy support."""
    
    BASE_URL = "https://openrouter.ai/api/v1"
    
    def __init__(self, api_key: str, proxy_url: Optional[str] = None, 
                 verify_ssl: bool = True, referer: str = "https://example.com",
                 app_title: str = "OpenRouterTester"):
        self.api_key = api_key
        self.proxy_url = proxy_url
        self.verify_ssl = verify_ssl
        self.referer = referer
        self.app_title = app_title
        
    def _get_headers(self) -> Dict[str, str]:
        """Build common headers for API requests."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        # Add optional headers for non-localhost keys
        if not self.api_key.startswith("sk-or-v1-local"):
            headers["HTTP-Referer"] = self.referer
            headers["X-Title"] = self.app_title
            
        return headers
    
    def _get_proxies(self) -> Optional[Dict[str, str]]:
        """Build proxy configuration if enabled."""
        if self.proxy_url:
            return {
                "http": self.proxy_url,
                "https": self.proxy_url
            }
        return None
    
    def _make_request(self, method: str, endpoint: str, 
                      data: Optional[Dict] = None, timeout: int = 30) -> Dict:
        """Make HTTP request with error handling."""
        url = f"{self.BASE_URL}{endpoint}"
        headers = self._get_headers()
        proxies = self._get_proxies()
        
        try:
            if method.upper() == "GET":
                response = requests.get(
                    url, 
                    headers=headers, 
                    proxies=proxies, 
                    verify=self.verify_ssl,
                    timeout=timeout
                )
            elif method.upper() == "POST":
                response = requests.post(
                    url,
                    headers=headers,
                    json=data,
                    proxies=proxies,
                    verify=self.verify_ssl,
                    timeout=timeout
                )
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.Timeout:
            raise Exception(f"Request timed out after {timeout} seconds")
        except requests.exceptions.ConnectionError as e:
            raise Exception(f"Connection error: {str(e)}")
        except requests.exceptions.HTTPError as e:
            raise Exception(f"HTTP error {response.status_code}: {response.text}")
        except json.JSONDecodeError:
            raise Exception("Invalid JSON response from server")
        except Exception as e:
            raise Exception(f"Request failed: {str(e)}")
    
    def get_key_info(self) -> Dict:
        """
        Get API key information including limits and usage.
        Returns: Dictionary with key details
        """
        try:
            response = self._make_request("GET", "/auth/key")
            data = response.get("data", {})
            return data
            
        except Exception as e:
            raise Exception(f"Failed to fetch key info: {str(e)}")
    
    def list_models(self, include_pricing: bool = False) -> List[Dict[str, str]]:
        """
        Get list of available chat/text models.
        Args:
            include_pricing: If True, include pricing and capability details
        Returns: List of {id, name, description, pricing, context_length} dicts
        """
        try:
            response = self._make_request("GET", "/models")
            models_data = response.get("data", [])
            
            chat_models = []
            excluded_types = ["embedding", "rerank", "moderation", "image", "audio", "llama-guard"]
            
            for model in models_data:
                model_id = model.get("id", "")
                
                # Filter out non-chat models by ID heuristics
                if any(excluded in model_id.lower() for excluded in excluded_types):
                    continue
                
                # Check architecture field if available
                architecture = model.get("architecture", {})
                if architecture:
                    modality = architecture.get("modality", "")
                    if modality and "text" not in modality.lower():
                        continue
                
                model_info = {
                    "id": model_id,
                    "name": model.get("name", model_id),
                    "description": model.get("description", "No description available")
                }
                
                # Add pricing information if requested
                if include_pricing:
                    pricing = model.get("pricing", {})
                    context_length = model.get("context_length", 0)
                    
                    # Convert pricing to readable format (per million tokens)
                    prompt_price = float(pricing.get("prompt", 0)) * 1_000_000 if pricing.get("prompt") else 0
                    completion_price = float(pricing.get("completion", 0)) * 1_000_000 if pricing.get("completion") else 0
                    image_price = float(pricing.get("image", 0)) * 1_000_000 if pricing.get("image") else 0
                    
                    # Build pricing display string
                    pricing_parts = []
                    if context_length:
                        # Format context length
                        if context_length >= 1_000_000:
                            pricing_parts.append(f"[ {context_length/1_000_000:.1f}M ctx ]")
                        elif context_length >= 1_000:
                            pricing_parts.append(f"[ {context_length/1_000:.0f}K ctx ]")
                        else:
                            pricing_parts.append(f"[ {context_length} ctx ]")
                    
                    if prompt_price > 0:
                        pricing_parts.append(f"\t[ ${prompt_price:.2f}/M in")
                    if completion_price > 0:
                        pricing_parts.append(f"${completion_price:.2f}/M out ]")
                    if image_price > 0:
                        pricing_parts.append(f"[ ${image_price:.2f}/M img ]")
                    
                    model_info["pricing_display"] = ", ".join(pricing_parts) if pricing_parts else "Free"
                    model_info["context_length"] = context_length
                    model_info["prompt_price"] = prompt_price
                    model_info["completion_price"] = completion_price
                
                chat_models.append(model_info)
            
            return sorted(chat_models, key=lambda x: x["id"])
            
        except Exception as e:
            raise Exception(f"Failed to fetch models: {str(e)}")
    
    def chat(self, model_id: str, system_prompt: str, user_prompt: str,
             temperature: float = 0.7, top_p: float = 0.95, 
             top_k: int = 40, max_tokens: int = 1024, 
             enable_reasoning: bool = False) -> Tuple[str, Dict]:
        """
        Send chat completion request with optional reasoning.
        Returns: (response_text, usage_dict)
        """
        # Validate parameters
        temperature = max(0.0, min(2.0, temperature))
        top_p = max(0.0, min(1.0, top_p))
        top_k = max(1, top_k)
        max_tokens = max(1, max_tokens)
        
        messages = []
        if system_prompt and system_prompt.strip():
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_prompt})
        
        payload = {
            "model": model_id,
            "messages": messages,
            "temperature": temperature,
            "top_p": top_p,
            "top_k": top_k,
            "max_tokens": max_tokens,
            "usage": {"include": True}
        }
        
        # Add reasoning parameters if enabled
        if enable_reasoning:
            payload["reasoning"] = {"enabled": True}
        
        try:
            response = self._make_request("POST", "/chat/completions", data=payload, timeout=120)
            
            # Extract response text
            choices = response.get("choices", [])
            if not choices:
                raise Exception("No response choices returned")
            
            message = choices[0].get("message", {})
            content = message.get("content", "")
            
            # Extract usage information
            usage = response.get("usage", {})
            
            return content, usage
            
        except Exception as e:
            raise Exception(f"Chat request failed: {str(e)}")

