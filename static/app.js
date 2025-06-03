document.addEventListener('DOMContentLoaded', () => {
    const socket = io();
    const startButton = document.getElementById('startButton');
    const statusDiv = document.getElementById('status');
    const messagesDiv = document.getElementById('messages');
    const voiceSelect = document.getElementById('voice-select');
    const scenarioCards = document.querySelectorAll('.scenario-card');
    const currentScenarioDiv = document.getElementById('current-scenario');
    const conversationDiv = document.getElementById('conversation');
    const feedbackPanel = document.getElementById('feedback-panel');
    const feedbackContent = document.getElementById('feedback-content');
    
    let recognition = null;
    let isListening = false;
    let currentScenario = null;
    let shouldRestartRecognition = false;
    let transcriptBuffer = '';
    let transcriptTimeout = null;
    
    // Audio queue management
    const audioQueue = [];
    let isPlaying = false;
    
    function playNextInQueue() {
        if (audioQueue.length === 0 || isPlaying) {
            return;
        }
        
        isPlaying = true;
        const nextAudio = audioQueue[0];
        const audio = new Audio(nextAudio.url);
        
        // Pause recognition while playing audio
        if (recognition && isListening) {
            shouldRestartRecognition = true;
            recognition.stop();
        }
        
        audio.onended = () => {
            audioQueue.shift(); // Remove the played audio from queue
            isPlaying = false;
            
            // Resume recognition if it was active
            if (shouldRestartRecognition && recognition) {
                setTimeout(() => {
                    if (isListening) {
                        recognition.start();
                    }
                }, 500); // Add a small delay before restarting recognition
            }
            
            playNextInQueue(); // Play next audio if available
        };
        
        audio.onerror = (error) => {
            console.error('Error playing audio:', error);
            audioQueue.shift(); // Remove the errored audio
            isPlaying = false;
            
            // Resume recognition if it was active
            if (shouldRestartRecognition && recognition) {
                setTimeout(() => {
                    if (isListening) {
                        recognition.start();
                    }
                }, 500);
            }
            
            playNextInQueue(); // Try next audio
        };
        
        audio.play().catch(error => {
            console.error('Error playing audio:', error);
            audioQueue.shift();
            isPlaying = false;
            
            // Resume recognition if it was active
            if (shouldRestartRecognition && recognition) {
                setTimeout(() => {
                    if (isListening) {
                        recognition.start();
                    }
                }, 500);
            }
            
            playNextInQueue();
        });
    }
    
    function queueAudioResponse(audioUrl, text) {
        audioQueue.push({ url: audioUrl, text: text });
        playNextInQueue();
    }
    
    // Initialize speech recognition
    if ('webkitSpeechRecognition' in window) {
        recognition = new webkitSpeechRecognition();
        recognition.continuous = true; // Changed back to true to handle continuous speech
        recognition.interimResults = true; // Enable interim results to handle pauses better
        
        recognition.onstart = () => {
            statusDiv.textContent = '🎤 Listening...';
            startButton.classList.add('listening');
            transcriptBuffer = ''; // Clear buffer when starting new recognition
        };
        
        recognition.onend = () => {
            if (isListening && !isPlaying) {
                recognition.start();
            } else {
                statusDiv.textContent = isPlaying ? 'AI is speaking...' : 'Ready...';
                startButton.classList.remove('listening');
            }
        };
        
        recognition.onresult = (event) => {
            // Clear any pending timeout
            if (transcriptTimeout) {
                clearTimeout(transcriptTimeout);
            }
            
            // Get the latest transcript
            let interimTranscript = '';
            let finalTranscript = '';
            
            for (let i = event.resultIndex; i < event.results.length; ++i) {
                const transcript = event.results[i][0].transcript;
                if (event.results[i].isFinal) {
                    finalTranscript += transcript;
                } else {
                    interimTranscript += transcript;
                }
            }
            
            // Update the buffer with any final transcript
            if (finalTranscript) {
                transcriptBuffer += finalTranscript;
            }
            
            // Show interim results in a temporary way (optional)
            if (interimTranscript) {
                statusDiv.textContent = '🎤 Listening... "' + interimTranscript + '"';
            }
            
            // Set a timeout to send the complete utterance
            transcriptTimeout = setTimeout(() => {
                if (transcriptBuffer.trim()) {
                    addMessage('user', transcriptBuffer);
                    socket.emit('transcribe', {
                        text: transcriptBuffer,
                        voice: voiceSelect.value,
                        scenario_id: currentScenario.id
                    });
                    transcriptBuffer = ''; // Clear the buffer after sending
                }
            }, 1500); // Wait 1.5 seconds after speech pause before sending
        };
        
        recognition.onerror = (event) => {
            console.error('Speech recognition error:', event.error);
            statusDiv.textContent = `Error: ${event.error}`;
            if (transcriptTimeout) {
                clearTimeout(transcriptTimeout);
            }
        };
    } else {
        startButton.disabled = true;
        statusDiv.textContent = 'Speech recognition not supported';
    }
    
    // Scenario selection handlers
    scenarioCards.forEach(card => {
        card.addEventListener('click', () => {
            // Reset previous scenario if any
            if (isListening) {
                recognition.stop();
                isListening = false;
                startButton.textContent = 'Start Conversation';
                startButton.classList.remove('listening');
            }
            
            // Clear audio queue
            audioQueue.length = 0;
            isPlaying = false;
            shouldRestartRecognition = false;
            
            // Update UI
            scenarioCards.forEach(c => c.classList.remove('border-blue-500', 'border-2'));
            card.classList.add('border-blue-500', 'border-2');
            
            // Get scenario data
            currentScenario = {
                id: card.dataset.scenarioId,
                title: card.querySelector('h3').textContent,
                description: card.querySelector('p').textContent
            };
            
            // Update current scenario display
            document.getElementById('scenario-title').textContent = currentScenario.title;
            document.getElementById('scenario-description').textContent = currentScenario.description;
            
            // Show relevant sections
            currentScenarioDiv.classList.remove('hidden');
            conversationDiv.classList.remove('hidden');
            startButton.classList.remove('hidden');
            feedbackPanel.classList.add('hidden');
            
            // Clear previous conversation
            messagesDiv.innerHTML = '';
            
            if (transcriptTimeout) {
                clearTimeout(transcriptTimeout);
            }
            transcriptBuffer = '';
            
            // Start the scenario
            socket.emit('start_scenario', {
                scenario_id: currentScenario.id,
                voice: voiceSelect.value
            });
        });
    });
    
    // Socket.io event handlers
    socket.on('connect', () => {
        console.log('Connected to server');
    });
    
    socket.on('scenario_started', (data) => {
        addMessage('ai', data.message);
        if (data.audio_url) {
            queueAudioResponse(data.audio_url, data.message);
        }
        statusDiv.textContent = 'Ready to start conversation...';
    });
    
    socket.on('ai_response', (data) => {
        addMessage('ai', data.response);
        if (data.audio_url) {
            queueAudioResponse(data.audio_url, data.response);
        }
        
        // Display feedback
        feedbackPanel.classList.remove('hidden');
        feedbackContent.textContent = data.feedback;
    });
    
    socket.on('error', (data) => {
        statusDiv.textContent = `Error: ${data.message}`;
    });
    
    // Button click handler
    startButton.addEventListener('click', () => {
        if (!isListening) {
            isListening = true;
            shouldRestartRecognition = true;
            transcriptBuffer = ''; // Clear buffer when starting new conversation
            startButton.textContent = 'Stop Conversation';
            if (!isPlaying) {
                recognition.start();
            }
        } else {
            isListening = false;
            shouldRestartRecognition = false;
            if (transcriptTimeout) {
                clearTimeout(transcriptTimeout);
            }
            startButton.textContent = 'Start Conversation';
            recognition.stop();
        }
    });
    
    // Helper function to add messages to the conversation
    function addMessage(sender, text) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}-message`;
        messageDiv.textContent = `${sender === 'user' ? 'You' : 'AI'}: ${text}`;
        messagesDiv.appendChild(messageDiv);
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
    }
}); 