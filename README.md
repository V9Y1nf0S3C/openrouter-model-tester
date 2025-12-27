# OpenRouter Model Tester

A comprehensive GUI application for testing and comparing multiple LLM models through OpenRouter API, designed for security professionals, developers, and AI researchers.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)

## 🎯 Features

### Multi-Model Testing
- **100+ Models Supported**: OpenAI, Anthropic, Google, Meta, Mistral, DeepSeek, and more
- **Batch Execution**: Test multiple models with identical prompts
- **Reasoning Model Detection**: Visual indicators for o1, o3, DeepThink models
- **Smart Filtering**: Skip embeddings, image-only, and irrelevant models automatically
- **Intelligent Sorting**: Sort by input cost, output cost, or context window size

### Security-First Design
- **Proxy Support**: Route traffic through Burp Suite for security analysis
- **SSL Verification Toggle**: For testing environments
- **API Key Masking**: Show/hide toggle for credential safety

### Cost Management
- **Multi-Currency Display**: USD, INR, and Paisa (₹0.0001 precision)
- **Real-Time Balance Tracking**: Monitor API credit usage with percentage changes
- **Detailed Breakdowns**: Input/output token costs per model
- **Summary Tables**: Complete cost analysis post-execution
- **Context Overflow Detection**: Warns when costs incurred without response

### User Experience
- **Collapsible Sections**: Organize interface by workflow stage (API Config, Model Selection, Parameters, Execution)
- **Configuration Management**: Save/load complete test setups for reproducibility
- **Horizontal Scrolling**: All list views support horizontal scroll for long model names

## 📋 Requirements

- Python 3.8 or higher
- `tkinter` (usually included with Python)
- `requests` library
- `urllib3` library

## 🚀 Installation

```bash
# Clone the repository
git clone https://github.com/V9Y1nf0S3C/openrouter-model-tester.git
cd openrouter-model-tester

# Install dependencies
pip install -r requirements.txt

# Run the application
python gui.py
```

### requirements.txt
```
requests>=2.31.0
urllib3>=2.0.0
```

## 📖 Usage

### Basic Workflow

1. **Configure API**
   - Enter your OpenRouter API key (get one at [OpenRouter.ai](https://openrouter.ai))
   - (Optional) Enable proxy routing through Burp Suite (e.g., `http://127.0.0.1:8080`)
   - Click eye icon (👁) to show/hide API key

2. **Load Models**
   - Click "Load Models" to fetch available models (cached for session)
   - Use search box to filter models by name
   - Apply skip filter to exclude embeddings, image models, etc.
   - Sort by input price, output price, or context window size

3. **Select Models**
   - **Single-click** to select a model line
   - **Shift+Click** to select multiple lines
   - **Double-click** to instantly add a model
   - **Ctrl+A** to select all visible models
   - Click "Add →" button or press Enter

4. **Set Parameters**
   - Adjust temperature (0.0-2.0), top-p (0.0-1.0), top-k (1-100), max_tokens (1-4096)
   - Enter system and user prompts
   - (Optional) Enable reasoning for compatible models (o1, o3, DeepThink)
   - Click "Reset to Default" to restore default parameters

5. **Execute & Analyze**
   - Click "Run on Selected Models"
   - View real-time responses and cost breakdowns
   - Check detailed summary table for totals across all models
   - Use "Check Key Balance" to verify credit usage

### Configuration Files

Save your test setup for reproducibility:

```json
{
  "api_key": "sk-or-v1-...",
  "temperature": 0.7,
  "top_p": 0.95,
  "top_k": 40,
  "max_tokens": 1024,
  "enable_reasoning": false,
  "selected_models": [
    "openai/gpt-4o",
    "anthropic/claude-3-5-sonnet",
    "google/gemini-2.0-flash-exp"
  ],
  "system_prompt": "You are a helpful assistant",
  "user_prompt": "Explain quantum computing in simple terms"
}
```

**To Save/Load:**
- Click "Save Config" button → Choose location → Save as JSON
- Click "Load Config" button → Select JSON file → All settings restored

## 🔐 Security Use Cases

### 1. Prompt Injection Testing
Route requests through Burp Suite to:
- Analyze API payloads and headers
- Test injection vectors (system prompt override, context escaping)
- Intercept and modify responses
- Monitor token consumption patterns

### 2. Cost Attack Simulation
Test how malicious prompts affect:
- Token consumption rates
- Context window overflow behavior
- API credit exhaustion vectors
- Rate limiting responses

### 3. Model Behavior Analysis
Compare responses across models for:
- Jailbreak attempt effectiveness
- Content policy violations
- Bias detection and consistency
- Reasoning capability differences

### 4. LLM Red Teaming
- Test identical adversarial prompts across 50+ models
- Identify vulnerable models in seconds
- Document findings with saved logs
- Generate cost-effective testing strategies

## 📊 Example Output

Testing 15 different models simultaneously with identical prompts:

```
==================================================================================================================================
DETAILED EXECUTION SUMMARY
==================================================================================================================================
Model                                         In Tok     Out Tok    Total      Cost In      Cost Out     Total USD    Total INR      Paisa     
----------------------------------------------------------------------------------------------------------------------------------
opengvlab/internvl3-78b (FAILED)              0          0          0          $0.0000000   $0.0000000   $0.0000000   ₹0.0000        0.00      
openai/gpt-5-mini                             23         290        313        $0.0000058   $0.0005800   $0.0005858   ₹0.0524        5.24      
google/gemini-3-flash-preview                 15         25         40         $0.0000075   $0.0000750   $0.0000825   ₹0.0074        0.74      
amazon/nova-lite-v1                           13         33         46         $0.0000008   $0.0000079   $0.0000087   ₹0.0008        0.08      
anthropic/claude-3.7-sonnet                   20         35         55         $0.0000600   $0.0005250   $0.0005850   ₹0.0524        5.24      
baidu/ernie-4.5-21b-a3b                       21         51         72         $0.0000012   $0.0000114   $0.0000126   ₹0.0011        0.11      
deepcogito/cogito-v2-preview-llama-109b-moe   28         34         62         $0.0000050   $0.0000201   $0.0000251   ₹0.0022        0.22      
deepseek/deepseek-v3.2-speciale               17         1024       1041       $0.0000068   $0.0005120   $0.0005188   ₹0.0464        4.64      
meta-llama/llama-3.2-90b-vision-instruct      28         35         63         $0.0000098   $0.0000140   $0.0000238   ₹0.0021        0.21      
meta-llama/llama-4-maverick                   29         32         61         $0.0000078   $0.0000272   $0.0000350   ₹0.0031        0.31      
microsoft/phi-4-reasoning-plus                24         109        133        $0.0000017   $0.0000382   $0.0000398   ₹0.0036        0.36      
mistralai/voxtral-small-24b-2507              18         16         34         $0.0000018   $0.0000048   $0.0000066   ₹0.0006        0.06      
nvidia/nemotron-3-nano-30b-a3b                29         72         101        $0.0000017   $0.0000173   $0.0000190   ₹0.0017        0.17      
x-ai/grok-4.1-fast                            169        227        396        $0.0000113   $0.0001135   $0.0001248   ₹0.0112        1.12      
z-ai/glm-4.5-air                              24         17         41         $0.0000018   $0.0000116   $0.0000133   ₹0.0012        0.12      
----------------------------------------------------------------------------------------------------------------------------------
TOTAL                                         458        2000       2458       $0.0001230   $0.0019579   $0.0020809   ₹0.1862        18.62     
==================================================================================================================================
Models Executed: 15
Total Cost: $0.0020809 USD (₹0.1862 INR / 18.62 paisa)
Average Cost: $0.0001387 USD (₹0.0124 INR / 1.24 paisa)
Average Tokens: 163
Exchange Rate: 1 USD = 89.5 INR = 8950 paisa
==================================================================================================================================
```

**Key Insights from this Test:**
- ✅ **14 successful executions** + 1 failed model (handled gracefully)
- 💰 **Total cost: ₹0.19 INR** (less than 20 paisa for 15 models!)
- 📊 **Token usage**: 458 input tokens, 2000 output tokens across all models
- ⚡ **Cost efficiency**: Amazon Nova Lite (₹0.0008) vs OpenAI GPT-5 Mini (₹0.0524) - 65x cheaper
- 🎯 **Average cost per model**: ₹0.0124 INR (1.24 paisa)

## 🛠️ Architecture

```
openrouter-model-tester/
├── gui.py              # Main application (Tkinter UI + CollapsibleFrame)
├── api_client.py       # OpenRouter API wrapper with proxy support
├── logging_utils.py    # Dual logging (file + GUI widget)
├── requirements.txt    # Python dependencies
├── README.md          # This file
└── LICENSE            # MIT License
```

## 📁 File Descriptions

### gui.py
Main application with:
- `OpenRouterGUI` class - Main window and widget management
- `CollapsibleFrame` class - Expandable/collapsible UI sections
- Model selection, filtering, and sorting logic
- Configuration save/load with validation
- Threaded execution to prevent UI freezing

### api_client.py
OpenRouter API client with:
- `OpenRouterClient` class - HTTP request handling
- Proxy support configuration
- SSL verification toggle
- Usage tracking and cost calculation
- Error handling and retries

### logging_utils.py
Dual logging system:
- `DualLogger` class - Simultaneous file and GUI logging
- Formatted output for readability
- Detailed summary table generation
- Color-coded log levels (INFO, WARNING, ERROR)

## 🤝 Contributing

Contributions welcome! Please follow these guidelines:

1. **Security Issues**: Report privately via GitHub Security tab or email
2. **Feature Requests**: Open an issue with detailed use case and rationale
3. **Pull Requests**: 
   - Fork the repository
   - Create a feature branch (`git checkout -b feature/amazing-feature`)
   - Commit changes (`git commit -m 'Add amazing feature'`)
   - Push to branch (`git push origin feature/amazing-feature`)
   - Open a Pull Request with description and screenshots

### Development Setup

```bash
# Clone your fork
git clone https://github.com/V9Y1nf0S3C/openrouter-model-tester.git
cd openrouter-model-tester

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run tests (if available)
python -m pytest tests/

# Run the application
python gui.py
```

## 🐛 Troubleshooting

### macOS Warning: "Expected min height of view"
Add at the top of `gui.py`:
```python
import os
os.environ['TK_SILENCE_DEPRECATION'] = '1'
```

### SSL Certificate Warnings
When using Burp Suite proxy, warnings are expected. They are automatically suppressed in the code.

### Models Not Loading
- Check API key is valid (test at [OpenRouter.ai](https://openrouter.ai))
- Verify internet connection
- Check firewall/proxy settings
- Review logs window for error messages

### High Costs
- Set lower `max_tokens` values (e.g., 256 instead of 1024)
- Test with cheaper models first (e.g., `openai/gpt-4o-mini`)
- Monitor balance frequently using "Check Key Balance"
- Enable skip filter to exclude expensive image models

## ✍️ Author & Creative Credit

* **[Vinaya Kumar/V9Y1nf0S3C] , [Jay/appsecjay]** - *Lead Developer & Architect* * Designed the tool architecture, UI/UX flow, and cost-calculation logic.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

**Copyright (c) 2025 [Vinaya Kumar]**

## 🙏 Acknowledgments

- **OpenRouter** for providing unified LLM API access across multiple providers
- **Cybersecurity Community** for testing, feedback, and feature suggestions
- **Contributors** who reported bugs and submitted pull requests
- **Python & Tkinter** communities for excellent documentation

## 📧 Contact

- **GitHub Issues**: [Report bugs or request features](https://github.com/V9Y1nf0S3C/openrouter-model-tester/issues)
- **LinkedIn**: [[Vinaya Kumar](https://www.linkedin.com/in/vinay-vapt/)], [[Jay](https://www.linkedin.com/in/appsecjay/)]
 

## 🔗 References

- [OpenRouter API Documentation](https://openrouter.ai/docs)
- [Burp Suite Community Edition](https://portswigger.net/burp/communitydownload)
- [OWASP LLM Top 10](https://owasp.org/www-project-top-10-for-large-language-model-applications/)

## ⚠️ Disclaimer

This tool is for **research, testing, and educational purposes**. Users are responsible for:
- Compliance with OpenRouter Terms of Service
- API key security and cost management
- Ethical use of AI models and testing methodologies
- Adherence to applicable laws and regulations

**Do not use this tool for:**
- Unauthorized access or testing of systems
- Generating harmful, illegal, or unethical content
- Violating model provider usage policies
- Production deployments without proper security review


**Made with ❤️ by the AI Security Community**

**Star ⭐ this repo if you find it useful!**
