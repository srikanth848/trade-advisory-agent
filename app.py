import os
from dotenv import load_dotenv

# 1. Load environment variables FIRST
load_dotenv()

# 2. Import the Supervisor orchestrator
from supervisor import Supervisor

def main():
    print("Trade Advisory Agent CLI")
    print("Type 'exit' or 'quit' to leave.\n")
    
    # Initialize the central Supervisor instance
    agent_supervisor = Supervisor()

    while True:
        try:
            user_input = input("You: ").strip()
            if not user_input:
                continue
            if user_input.lower() in ["exit", "quit"]:
                break
            
            # Pass user prompt to Supervisor (handles symbol resolution & parallel dispatch internally)
            response = agent_supervisor.handle(user_input)
            
            # If a direct sub-agent string was returned instead of streaming
            if response:
                print(f"\n{response}\n")
                
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"[Error] {e}")

if __name__ == "__main__":
    main()