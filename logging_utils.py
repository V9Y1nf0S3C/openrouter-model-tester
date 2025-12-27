import logging
from datetime import datetime
from typing import Optional
import tkinter as tk
from decimal import Decimal

class DualLogger:
    """Logger that writes to both file and GUI text widget."""
    
    def __init__(self, log_file: str = None, text_widget: Optional[tk.Text] = None):
        self.text_widget = text_widget
        
        # Generate log filename if not provided
        if log_file is None:
            log_file = f"{datetime.now().strftime('%Y%m%d')}-openrouter-log.txt"
        
        self.log_file = log_file
        
        # Configure file logging
        logging.basicConfig(
            filename=self.log_file,
            level=logging.INFO,
            format='%(asctime)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        self.logger = logging.getLogger('OpenRouterTester')
    
    def log(self, message: str, level: str = "INFO"):
        """Write message to both file and GUI."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        formatted_message = f"[{timestamp}] {message}"
        
        # Log to file
        if level == "ERROR":
            self.logger.error(message)
        elif level == "WARNING":
            self.logger.warning(message)
        else:
            self.logger.info(message)
        
        # Log to GUI if widget available
        if self.text_widget:
            self.text_widget.insert(tk.END, formatted_message + "\n")
            self.text_widget.see(tk.END)
            self.text_widget.update_idletasks()
    
    def separator(self, char: str = "=", length: int = 80):
        """Add a visual separator line."""
        self.log(char * length)
    
    def model_header(self, model_id: str):
        """Log a model execution header."""
        self.separator()
        self.log(f"MODEL: {model_id}")
        self.separator()
    
    def log_key_balance(self, key_info: dict):
        """Log API key balance and limits with percentage."""
        try:
            limit = key_info.get("limit", 0)
            usage = key_info.get("usage", 0)
            
            limit_decimal = Decimal(str(limit))
            usage_decimal = Decimal(str(usage))
            remaining = limit_decimal - usage_decimal
            
            # Calculate percentage remaining
            if limit_decimal > 0:
                percentage_remaining = (remaining / limit_decimal) * 100
                self.log(f"Key Balance - Total: ${limit_decimal:.7f} | Used: ${usage_decimal:.7f} | Remaining: ${remaining:.7f} ({percentage_remaining:.2f}%)")
            else:
                self.log(f"Key Balance - Total: ${limit_decimal:.7f} | Used: ${usage_decimal:.7f} | Remaining: ${remaining:.7f}")
                
        except Exception as e:
            self.log(f"Error logging key balance: {str(e)}", level="WARNING")


    def log_detailed_summary_table(self, execution_results: list, usd_to_inr: float = 83.5):
        """Log detailed summary table with paisa column."""
        if not execution_results:
            self.log("No execution results to summarize")
            return
        
        self.separator("=", 130)
        self.log("DETAILED EXECUTION SUMMARY")
        self.separator("=", 130)
        
        header = f"{'Model':<45} {'In Tok':<10} {'Out Tok':<10} {'Total':<10} {'Cost In':<12} {'Cost Out':<12} {'Total USD':<12} {'Total INR':<14} {'Paisa':<10}"
        self.log(header)
        self.separator("-", 130)
        
        total_prompt_tokens = 0
        total_completion_tokens = 0
        total_tokens = 0
        total_cost_usd = Decimal("0")
        total_input_cost = Decimal("0")
        total_output_cost = Decimal("0")
        
        for result in execution_results:
            model_name = result.get("model", "Unknown")[:43]
            prompt_tokens = result.get("prompt_tokens", 0)
            completion_tokens = result.get("completion_tokens", 0)
            tokens = result.get("total_tokens", 0)
            
            input_cost = result.get("input_cost_usd", Decimal("0"))
            output_cost = result.get("output_cost_usd", Decimal("0"))
            cost_usd = result.get("cost_usd", Decimal("0"))
            cost_inr = cost_usd * Decimal(str(usd_to_inr))
            cost_paisa = cost_inr * 100  # 1 INR = 100 paisa
            
            total_prompt_tokens += prompt_tokens
            total_completion_tokens += completion_tokens
            total_tokens += tokens
            total_cost_usd += cost_usd
            total_input_cost += input_cost
            total_output_cost += output_cost
            
            row = f"{model_name:<45} {prompt_tokens:<10} {completion_tokens:<10} {tokens:<10} ${input_cost:<11.7f} ${output_cost:<11.7f} ${cost_usd:<11.7f} ₹{cost_inr:<13.4f} {cost_paisa:<10.2f}"
            self.log(row)
        
        self.separator("-", 130)
        total_cost_inr = total_cost_usd * Decimal(str(usd_to_inr))
        total_paisa = total_cost_inr * 100
        total_row = f"{'TOTAL':<45} {total_prompt_tokens:<10} {total_completion_tokens:<10} {total_tokens:<10} ${total_input_cost:<11.7f} ${total_output_cost:<11.7f} ${total_cost_usd:<11.7f} ₹{total_cost_inr:<13.4f} {total_paisa:<10.2f}"
        self.log(total_row)
        self.separator("=", 130)
        
        if len(execution_results) > 0:
            avg_cost_usd = total_cost_usd / len(execution_results)
            avg_cost_inr = avg_cost_usd * Decimal(str(usd_to_inr))
            avg_paisa = avg_cost_inr * 100
            avg_tokens = total_tokens // len(execution_results)
            
            self.log(f"Models Executed: {len(execution_results)}")
            self.log(f"Total Cost: ${total_cost_usd:.7f} USD (₹{total_cost_inr:.4f} INR / {total_paisa:.2f} paisa)")
            self.log(f"Average Cost: ${avg_cost_usd:.7f} USD (₹{avg_cost_inr:.4f} INR / {avg_paisa:.2f} paisa)")
            self.log(f"Average Tokens: {avg_tokens}")
            self.log(f"Exchange Rate: 1 USD = {usd_to_inr} INR = {usd_to_inr * 100:.0f} paisa")
        
        self.separator("=", 130)





    def log_usage(self, usage: dict, execution_time: float = 0):
        """Log detailed usage and cost information with execution time."""
        try:
            # Extract cost details
            total_cost = usage.get("cost", 0)
            cost_details = usage.get("cost_details", {})
            
            # Token counts
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)
            total_tokens = usage.get("total_tokens", 0)
            
            # Detailed cost breakdown
            upstream_prompt_cost = cost_details.get("upstream_inference_prompt_cost", 0)
            upstream_completion_cost = cost_details.get("upstream_inference_completions_cost", 0)
            
            # Log token usage
            self.log(f"Tokens - Prompt: {prompt_tokens} | Completion: {completion_tokens} | Total: {total_tokens}")
            
            # Log execution time
            if execution_time > 0:
                self.log(f"Execution Time: {execution_time:.2f}s")
            
            # Log cost breakdown
            if total_cost > 0:
                total_cost_decimal = Decimal(str(total_cost))
                total_cost_inr = total_cost_decimal * Decimal("90")
                self.log(f"Total Cost: ${total_cost_decimal:.7f} (₹{total_cost_inr:.4f} INR)")

                # Cost as percentage of 1 cent
                cost_10c_percentage = (total_cost_decimal / Decimal("0.01")) * 100
                self.log(f"Cost vs 1¢: {cost_10c_percentage:.4f}% of 1 cent")
                
                if upstream_prompt_cost > 0:
                    prompt_cost_decimal = Decimal(str(upstream_prompt_cost))
                    self.log(f"  ├─ Input Tokens Cost: ${prompt_cost_decimal:.7f}")
                
                if upstream_completion_cost > 0:
                    completion_cost_decimal = Decimal(str(upstream_completion_cost))
                    self.log(f"  └─ Output Tokens Cost: ${completion_cost_decimal:.7f}")
                
                # Calculate requests per $1 & per 1.00 INR
                requests_per_dollar = Decimal("1.0") / total_cost_decimal
                requests_per_inr = requests_per_dollar / Decimal("90")
                self.log(f"Cost Efficiency: ~{requests_per_dollar:.0f} req/$1.00 (~{requests_per_inr:.0f} req/₹1.00)")
                                

            else:
                self.log("Total Cost: $0.00 (Free tier or error)")
            
            # Log BYOK status if available
            # is_byok = usage.get("is_byok")
            # if is_byok is not None:
            #     self.log(f"BYOK (Bring Your Own Key): {is_byok}")
                    
        except Exception as e:
            self.log(f"Error logging usage: {str(e)}", level="WARNING")

    
    def log_prompts(self, system_prompt: str, user_prompt: str):
        """Log the system and user prompts used for the request."""
        self.separator("-", 80)
        self.log("PROMPTS USED:")
        self.separator("-", 80)
        
        if system_prompt and system_prompt.strip():
            self.log("System Prompt:")
            # Split into lines for better readability in logs
            for line in system_prompt.strip().split('\n'):
                self.log(f"  {line}")
        else:
            self.log("System Prompt: (none)")
        
        self.log("")  # Empty line for separation
        self.log("User Prompt:")
        for line in user_prompt.strip().split('\n'):
            self.log(f"  {line}")
        
        self.separator("-", 80)
