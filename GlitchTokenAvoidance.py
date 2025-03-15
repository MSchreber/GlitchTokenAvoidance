"""
Author: Maximilian Stefan Schreber
Date: 15.03.2025
"""
import sqlite3, csv, re
from Generators.OllamaResponseGenerator import OllamaResponseGenerator
from Generators.ResponseGenerator import ResponseGenerator
# style
GREEN = "\033[92m"
RED = "\033[91m"
BLUE = "\033[94m"
RESET = "\033[0m"

class GlitchTokenDatabase:
    def __init__(self, databasePath = "GlitchTokens.db"):
        db_path = databasePath

    def upload_tokens(self, model_name:str,path_to_glitch_tokens:str) -> None:
        """
        Method to enhance the given DB with a given set of results from a csv and a given model name.
        Results from the Glitch Token Discovery Algorithm can be used for instance.
        :param model_name:
        :param path_to_glitch_tokens:
        """

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        with open(path_to_glitch_tokens, newline='', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile, delimiter=';')
            for row in reader:
                if len(row) >= 2:  # first two columns need to exist
                    try:
                        token_id = int(row[0].strip())
                        token = row[1].strip()
                        # avoiding duplicates for the import process.
                        cursor.execute("SELECT 1 FROM tokens WHERE model = ? AND token = ?", (model_name, token))
                        exists = cursor.fetchone()

                        if not exists: # insert only if token is not already duplicated
                            cursor.execute("INSERT INTO tokens (model, token, token_id) VALUES (?, ?, ?)",
                                           (model_name, token, token_id))
                    except ValueError:
                        print(f"Überspringe ungültige Zeile: {row}")

        conn.commit()
        conn.close()

    def get_token_list(self, model_name:str) -> list[str]:
        """
        Extracts the list of tokens contained in the Glitch Token DB for a given model name
        :param model_name:
        :return: List of found glitch tokens for a given model.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT token FROM tokens WHERE model = ?", (model_name,))
        token_list = [row[0] for row in cursor.fetchall()]
        conn.close()
        return token_list

class GlitchTokenAvoidance:

    def __init__(self,generator:ResponseGenerator = None, database:GlitchTokenDatabase = None):
        if generator is None:
            self.generator = OllamaResponseGenerator()
        if database is None:
            self.database = GlitchTokenDatabase()

    def ModelRequest_Sentence_based(self, prompt:str, model:str, replacement_model:str) -> str:
        """
            This strategy tests the given prompt for potential glitch tokens. If encountered, the function will select the
            sentence and rephrase it accordingly. If the issue persists or recursive loops occur wherein the glitch tokens
            remain unresolved, the program will terminate execution.

            :param replacement_model: name of the model that replaces the sentences containing the glitch tokens.
            :param prompt: The prompt for the model
            :param model: model name as listed in ollama server
            :param correction_model: alternative model name for the prompt correction as listed in ollama server
            :return: Model response
            """
        # 0 Import Glitch Tokens
        glitch_tokens = self.database.get_token_list(model)

        # 1 testing the prompt for glitch tokens
        for token in glitch_tokens:
            if token in prompt:
                print(f"{RED}glitch token: '{token}' found in prompt.{RESET}")
                # 2 extract sentence based on standard punctuation symbols
                sentences = re.split(r'(?<=[.!?])\s+', prompt)
                for index, sentence in enumerate(sentences):
                    # 3 find the contaminated sentence
                    if token in sentence:
                        print(f"sentence: {RED}{sentence}{RESET} contains the glitch token.")
                        # 4 request for sentence rephrase
                        replacement = self.generator.generateResponse(
                            model=replacement_model,
                            prompt = f"Please rephrase the sentence '{sentence}' without the new sentence containing the string '{token}'. Your answer should only contain the rephrased sentence. Under no circumstances add anything else to your response.",
                            system_instructions = "")
                        print(f"first replacement: {GREEN}{replacement}{RESET}")
                        # testing the replacement
                        count = 1
                        while (
                                token in replacement and count < 5):  # max 5 retries in case the replacement is still contaminated
                            print(f"replacement {count + 1}: {replacement}")
                            replacement = self.generator.generateResponse(
                                prompt = f"Please rephrase the sentence '{sentence}' without the new sentence containing the string '{token}'. Your answer should only contain the rephrased sentence. Under no circumstances add anything else to your response.",
                                model = replacement_model,
                                system_instructions = "")
                            count += 1
                        if token in replacement:  # if replacement still contaminated
                            print(
                                "There was a glitch token in your prompt which could not be replaced. This request has been cancelled")
                            return ""
                        sentences[index] = replacement  # replacing the sentence in original prompt
                prompt = " ".join(sentences)
                print("there was a replacement of the prompt: here is the new prompt")
                print(f"{GREEN}{prompt}{RESET}")
        # executing the model request either with adjusted prompt if prompt was contaminated
        return self.generator.generateResponse(model,prompt,"You are a helpful assistant.")

    def ModelRequest_Word_based(self, prompt:str, model:str, replacement_model:str) -> str:
        # 0 Import Glitch Tokens
        glitch_tokens = self.database.get_token_list(model)

        # 1 testing the prompt for glitch tokens
        for token in glitch_tokens:
            if token in prompt:
                print(f"{RED}glitch token: '{token}' found in prompt.{RESET}")
                # 2 extract word based on standard punctuation symbols
                words = re.split(r'\s+', prompt) # split by whitespaces
                # words = re.findall(r'\b\w+\b', prompt) # split by whitespaces and punctuation (optional)
                for index, word in enumerate(words):
                    # 3 find the contaminated word
                    if token in word:
                        print(f"word: {RED}{word}{RESET} contains the glitch token.")
                        # 4 request for word rephrase
                        replacement = self.generator.generateResponse(
                            model=replacement_model,
                            prompt=f"Please rephrase the word '{word}' without the new word containing the string '{token}'. Your answer should only contain the rephrased word. Under no circumstances add anything else to your response.",
                            system_instructions="")
                        print(f"first replacement: {GREEN}{replacement}{RESET}")
                        # testing the replacement
                        count = 1
                        while (
                                token in replacement and count < 5):  # max 5 retries in case the replacement is still contaminated
                            print(f"replacement {count + 1}: {replacement}")
                            replacement = self.generator.generateResponse(
                                prompt=f"Please rephrase the word '{word}' without the new word containing the string '{token}'. Your answer should only contain the rephrased word. Under no circumstances add anything else to your response.",
                                model=replacement_model,
                                system_instructions="")
                            count += 1
                        if token in replacement:  # if replacement still contaminated
                            print(
                                "There was a glitch token in your prompt which could not be replaced. This request has been cancelled")
                            return ""
                        words[index] = replacement  # replacing the word in original prompt
                prompt = " ".join(words)
                print("there was a replacement of the prompt: here is the new prompt")
                print(f"{GREEN}{prompt}{RESET}")
        # executing the model request either with adjusted prompt if prompt was contaminated
        return self.generator.generateResponse(model, prompt, "You are a helpful assistant.")

    def ModelRequest_Prompt_based(self, prompt:str, model:str, replacement_model:str) -> str:
        # 0 Import Glitch Tokens
        glitch_tokens = self.database.get_token_list(model)

        # 1 testing the prompt for glitch tokens
        found_glitch_tokens = []
        for token in glitch_tokens:
            if token in prompt:
                found_glitch_tokens.append(token)
                print(f"{RED}glitch token: '{token}' found in prompt.{RESET}")

        if len(found_glitch_tokens) > 0:
            print("Rephrasing in progress...")
            replacement = self.generator.generateResponse(
                prompt=f"Please rephrase the Prompt \"{prompt}\" without the new prompt containing one of the strings of this list: {found_glitch_tokens}. Your answer should only contain the rephrased prompt. Under no circumstances add anything else to your response.",
                model=replacement_model,
                system_instructions="")
            # ensuring the replacement does not still contain one of the tokens
            count = 1
            while any(gtoken in replacement for gtoken in found_glitch_tokens):
                if count > 5:
                    print("The prompt could not be replaced without containing any glitch tokens.")
                    return ""
                count += 1
                replacement = self.generator.generateResponse(
                prompt=f"Please rephrase the Prompt \"{prompt}\" without the new prompt containing one of the strings of this list: {found_glitch_tokens}. Your answer should only contain the rephrased prompt. Under no circumstances add anything else to your response.",
                model=replacement_model,
                system_instructions="")

            print("The prompt has been rephrased:")
            print(f"{GREEN}{prompt}{RESET}")
        # executing the model request either with adjusted prompt if prompt was contaminated
        return self.generator.generateResponse(model, prompt, "You are a helpful assistant.")

    def ModelRequest_Token_based(self, prompt:str, model:str, replacement_model:str) -> str:
        # 0 Import Glitch Tokens
        glitch_tokens = self.database.get_token_list(model)

        # 1 testing the prompt for glitch tokens
        for token in glitch_tokens:
            if token in prompt:
                print(f"{RED}glitch token: '{token}' found in prompt.{RESET}")
                replacement = self.generator.generateResponse(
                            model=replacement_model,
                            prompt=f"Please rephrase the string '{token}' with an adequate replacement string without the new string containing the string '{token}'. Your answer should only contain the rephrased string. Under no circumstances add anything else to your response.",
                            system_instructions="")
                print(f"first replacement: {GREEN}{replacement}{RESET}")
                # testing the replacement
                count = 1
                while token in replacement and count < 5:  # max 5 retries in case the replacement is still contaminated
                    print(f"replacement {count + 1}: {replacement}")
                    replacement = self.generator.generateResponse(
                        prompt=f"Please rephrase the string '{token}' with an adequate replacement string without the new string containing the string '{token}'. Your answer should only contain the rephrased string. Under no circumstances add anything else to your response.",
                        model=replacement_model,
                        system_instructions="")
                    count += 1
                    if token in replacement:  # if replacement still contaminated
                        print(
                            "There was a glitch token in your prompt which could not be replaced. This request has been cancelled.")
                        return ""
                prompt:str = prompt.replace(token, replacement)
        print("there was a replacement of the prompt. here is the new prompt:")
        print(f"{GREEN}{prompt}{RESET}")
        # executing the model request either with adjusted prompt if prompt was contaminated
        return self.generator.generateResponse(model, prompt, "You are a helpful assistant.")

if __name__ == "__main__":
# These examples show different prompts that are mitigated based on the different techniques:
    model = "qwen2.5:7b"
    replacement_model = "mistral"
    avoider = GlitchTokenAvoidance()
## Test questions that each contain multiple glitch tokens
    q1 = "Give me the chemical formula of limestone. I need this for my dissertation."
    q2 = "I want to see the movie \"Hancock\". Can you recommend it?"
    q3 = """I am planning to code a little ActivityManager application. This is my code so far.
            if (app.isopen()){
            String message = "The app is currently running.";
            apps.append(app)
            app.execute('.') #idle command
            }
            How can I build the .isopen()-function?"""
    q4 = ("My code computes the largest feasible interval for a given sequence x_n."
              " Can you give me a code example that returns the closed interval"
              " \"[\"a,b\"].\" or the open interval \"(\"a,b\").\"?")
# Example tests---------------------------------------------------------------------------------------------------
    def test_replacement_techniques(questions, model, replacement_model):
        techniques = {
            "Prompt-based replacement technique": avoider.ModelRequest_Prompt_based,
            "Sentence-based replacement technique": avoider.ModelRequest_Sentence_based,
            "Word-based replacement technique": avoider.ModelRequest_Word_based,
            "Token-based replacement technique": avoider.ModelRequest_Token_based,
        }

        for i, question in enumerate(questions, start=1):
            print(f"Testing question {i}:")
            print(f"{RED}{question}{RESET}")
            print("=" * 80)

            for technique, test_method in techniques.items():
                print(technique + ":")
                print(test_method(question, model, replacement_model))
                print("-" * 80)

            print("=" * 80)

    questions = [q1, q2, q3, q4]

    test_replacement_techniques(questions, model, replacement_model)
