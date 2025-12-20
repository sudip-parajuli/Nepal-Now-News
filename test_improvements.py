import asyncio
import os
from processors.classifier import NewsClassifier
from media.tts_english import TTSEngine

async def test_improvements():
    output = []
    output.append("--- Testing Breaking News Classification ---")
    classifier = NewsClassifier()
    
    test_items = [
        {"headline": "चितवनमा प्रमुख दुर्घटना, ५ जनाको मृत्यु", "content": "..."},
        {"headline": "ताजा अपडेट: चुनावको मिति घोषणा", "content": "..."},
        {"headline": "विशेष समाचार: नयाँ बजेट सार्वजनिक", "content": "..."},
        {"headline": "सामान्य मौसम अपडेट", "content": "..."}
    ]
    
    for item in test_items:
        result = classifier.classify(item)
        output.append(f"Headline: {item['headline']} -> Result: {result}")

    output.append("\n--- Testing TTS Abbreviation Expansion ---")
    test_texts = [
        "डा. राम भण्डारीले नयाँ अस्पताल खोल्नुभयो।",
        "इ. सुदीप पराजुलीले पुलको डिजाइन गर्नुभयो।",
        "वि.सं. २०८१ को फागुन महिना।"
    ]
    
    for text in test_texts:
        abbreviations = {
            r'डा\.': 'डाक्टर',
            r'इ\.': 'इन्जिनियर',
            r'ई\.': 'इन्जिनियर',
            r'प्रा\.': 'प्राध्यापक',
            r'प\.': 'पण्डित',
            r'वि\.सं\.': 'विक्रम सम्बत',
            r'नं\.': 'नम्बर',
            r'कि\.मी\.': 'किलोमिटर',
            r'मि\.': 'मिटर'
        }
        import re
        normalized = text.strip()
        for abbr, full in abbreviations.items():
            normalized = re.sub(abbr, full, normalized)
        
        output.append(f"Original: {text}")
        output.append(f"Expanded: {normalized}")

    with open("test_results.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(output))
    print("Results saved to test_results.txt")

if __name__ == "__main__":
    asyncio.run(test_improvements())
