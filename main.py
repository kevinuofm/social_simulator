import tkinter as tk
from tkinter import ttk, scrolledtext
import speech_recognition as sr
import threading
import queue
import time
from openai import OpenAI
import os
from dotenv import load_dotenv
import pyaudio

# Load environment variables
load_dotenv()

class SocialSimulatorGUI:
    def __init__(self):
        # Create main window
        self.root = tk.Tk()
        self.root.title("Social Simulator")
        self.root.geometry("800x600")
        
        # Create and configure main frame
        self.main_frame = ttk.Frame(self.root, padding="10")
        self.main_frame.grid(row=0, column=0, sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        
        # Create conversation display
        self.create_conversation_display()
        
        # Create status bar
        self.create_status_bar()
        
        # Create control buttons
        self.create_controls()
        
        # Configure weights for resizing
        self.main_frame.columnconfigure(0, weight=1)
        self.main_frame.rowconfigure(0, weight=1)
        
        # Initialize speech recognition with more lenient settings
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 4000  # Higher threshold
        self.recognizer.dynamic_energy_threshold = False  # Disable dynamic threshold
        self.recognizer.pause_threshold = 0.8  # Longer pause
        self.recognizer.phrase_threshold = 0.3  # Shorter phrase
        self.recognizer.non_speaking_duration = 0.5  # Shorter non-speaking duration
        
        # Find the default input device
        p = pyaudio.PyAudio()
        self.device_index = None
        print("\nAvailable input devices:")
        for i in range(p.get_device_count()):
            dev_info = p.get_device_info_by_index(i)
            if dev_info['maxInputChannels'] > 0:
                print(f"Device {i}: {dev_info['name']} (channels: {dev_info['maxInputChannels']})")
                if self.device_index is None:
                    self.device_index = i
        p.terminate()
        
        if self.device_index is None:
            self.update_conversation("No input device found!", "system")
            print("No input device found!")
        else:
            print(f"\nSelected device index: {self.device_index}")
        
        # Initialize OpenAI
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
        # Speech recognition thread control
        self.is_listening = False
        self.speech_thread = None
        
    def create_conversation_display(self):
        # Create and configure the conversation text area
        self.conversation = scrolledtext.ScrolledText(
            self.main_frame,
            wrap=tk.WORD,
            width=70,
            height=20,
            font=("Arial", 12)
        )
        self.conversation.grid(row=0, column=0, columnspan=2, sticky="nsew", padx=5, pady=5)
        
        # Configure text tags for different speakers
        self.conversation.tag_configure("ai", foreground="blue")
        self.conversation.tag_configure("user", foreground="green")
        self.conversation.tag_configure("system", foreground="gray")
        
    def create_status_bar(self):
        # Create and configure the status bar
        self.status_label = ttk.Label(
            self.main_frame,
            text="Ready...",
            anchor="center",
            padding=(5, 5)
        )
        self.status_label.grid(row=1, column=0, columnspan=2, sticky="ew", padx=5)
        
    def create_controls(self):
        # Create control buttons frame
        control_frame = ttk.Frame(self.main_frame)
        control_frame.grid(row=2, column=0, columnspan=2, sticky="ew", padx=5, pady=5)
        
        # Add Start button
        self.start_button = ttk.Button(
            control_frame,
            text="Start Listening",
            command=self.toggle_listening
        )
        self.start_button.pack(side=tk.LEFT, padx=5)
        
        # Add Exit button
        self.exit_button = ttk.Button(
            control_frame,
            text="Exit",
            command=self.quit_app
        )
        self.exit_button.pack(side=tk.RIGHT, padx=5)
        
    def toggle_listening(self):
        """Toggle speech recognition on/off"""
        if not self.is_listening:
            self.start_listening()
            self.start_button.configure(text="Stop Listening")
        else:
            self.stop_listening()
            self.start_button.configure(text="Start Listening")
            
    def start_listening(self):
        """Start the speech recognition thread"""
        self.is_listening = True
        self.speech_thread = threading.Thread(target=self.listen_loop)
        self.speech_thread.daemon = True
        self.speech_thread.start()
        self.update_status("🎤 Listening...")
        
    def stop_listening(self):
        """Stop the speech recognition thread"""
        self.is_listening = False
        if self.speech_thread:
            self.speech_thread.join(timeout=1)
        self.update_status("Stopped listening")
        
    def listen_loop(self):
        """Background thread for continuous speech recognition"""
        if self.device_index is None:
            error_msg = "No input device available!"
            print(error_msg)
            self.update_status(error_msg)
            self.update_conversation(error_msg, "system")
            return
            
        try:
            print("\nAttempting to initialize microphone...")
            with sr.Microphone(device_index=self.device_index, sample_rate=44100) as source:
                # Initial calibration
                print("Microphone initialized successfully")
                print(f"Using device index: {self.device_index}")
                self.update_status("🎤 Calibrating microphone...")
                
                try:
                    print("Starting calibration...")
                    self.recognizer.adjust_for_ambient_noise(source, duration=2)
                    current_energy = self.recognizer.energy_threshold
                    print(f"Calibration complete. Energy threshold: {current_energy}")
                    self.update_status(f"👂 Listening... (Energy threshold: {current_energy:.0f})")
                except Exception as e:
                    print(f"Error during calibration: {str(e)}")
                    raise
                
                while self.is_listening:
                    try:
                        print("Waiting for speech...")
                        audio = self.recognizer.listen(source, timeout=1, phrase_time_limit=10)
                        self.update_status("🔄 Processing speech...")
                        
                        try:
                            text = self.recognizer.recognize_google(audio)
                            print(f"Recognized text: {text}")
                            self.root.after(0, self.handle_speech, text)
                        except sr.UnknownValueError:
                            self.update_status("👂 Listening... (No speech detected)")
                        except sr.RequestError as e:
                            self.update_status(f"🚫 Error: {str(e)}")
                            
                    except sr.WaitTimeoutError:
                        continue
                        
        except Exception as e:
            error_msg = f"🎤 Microphone error: {str(e)}\nError type: {type(e).__name__}"
            print(error_msg)  # Print to console for debugging
            self.update_status(error_msg)
            self.update_conversation(error_msg, "system")
            # Stop listening since we encountered an error
            self.root.after(0, self.stop_listening)
            self.root.after(0, lambda: self.start_button.configure(text="Start Listening"))
            
    def handle_speech(self, text):
        """Process recognized speech"""
        self.update_conversation(f"You: {text}", "user")
        
        try:
            # Get AI response
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a friendly AI assistant having a casual conversation. Keep responses very concise, about 1-2 sentences."},
                    {"role": "user", "content": text}
                ],
                max_tokens=60
            )
            
            ai_response = response.choices[0].message.content.strip()
            self.update_conversation(f"AI: {ai_response}", "ai")
            
        except Exception as e:
            self.update_conversation(f"Error getting AI response: {str(e)}", "system")
            
        self.update_status("👂 Listening...")
        
    def update_conversation(self, text, speaker="system"):
        """Add a new message to the conversation"""
        self.conversation.insert(tk.END, f"{text}\n", speaker)
        self.conversation.see(tk.END)
        
    def update_status(self, status):
        """Update the status bar text"""
        self.root.after(0, lambda: self.status_label.config(text=status))
        
    def quit_app(self):
        """Clean up and quit the application"""
        self.stop_listening()
        self.root.quit()
        
    def run(self):
        """Start the GUI application"""
        # Show welcome message
        self.update_conversation("Welcome to Social Simulator!", "system")
        self.update_conversation("Click 'Start Listening' to begin.", "system")
        
        # Start the main event loop
        self.root.mainloop()

def main():
    app = SocialSimulatorGUI()
    app.run()

if __name__ == "__main__":
    main() 