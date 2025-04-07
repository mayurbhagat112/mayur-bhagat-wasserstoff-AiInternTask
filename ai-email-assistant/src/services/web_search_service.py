# src/services/web_search_service.py
from duckduckgo_search import DDGS
import time


def search_web(query, max_results=3):
    """
    Performs a web search using DuckDuckGo and returns formatted results.
    """
    print(f"[*] Performing web search for query: '{query}'")
    results_string = f"Web search results for '{query}':\n"
    try:
        # Use a context manager for DDGS object
        with DDGS() as ddgs:
            search_results = ddgs.text(query, max_results=max_results)

            if not search_results:
                print("[*] No search results found.")
                return f"No results found for '{query}'."

            count = 0
            for i, result in enumerate(search_results):
                if count >= max_results:
                    break
                title = result.get("title", "No Title")
                href = result.get("href", "#")
                body = result.get("body", "No snippet available.")
                results_string += f"{i+1}. {title} ({href})\n   {body}\n\n"
                count += 1

            print(f"[*] Web search successful. Found {count} results.")
            return results_string.strip()

    except Exception as e:
        print(f"[!] Error during web search: {e}")
        # Implement retry or fallback if necessary
        # Adding a small delay in case of frequent errors
        time.sleep(1)
        return f"Error occurred during web search for '{query}'."


# Example usage (for testing)
if __name__ == "__main__":
    test_query = "What is the capital of France?"
    search_results = search_web(test_query)
    print("\n--- Test Search Results ---")
    print(search_results)
    print("---------------------------")
