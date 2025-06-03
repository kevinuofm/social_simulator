# Social Simulator

An interactive web application for practicing social scenarios with AI-powered conversations.

## Features

- Real-time voice conversations with AI
- Multiple social scenarios (job interviews, networking, etc.)
- Voice selection options
- Real-time feedback
- Speech-to-text and text-to-speech capabilities

## Local Development

1. Clone the repository
2. Create a `.env` file with your OpenAI API key:
   ```
   OPENAI_API_KEY=your_api_key_here
   ```
3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
4. Run the development server:
   ```
   python app.py
   ```

## Deployment to Render

1. Create a new account on [Render](https://render.com)
2. Create a new Web Service
3. Connect your GitHub repository
4. Add your `OPENAI_API_KEY` in the Environment Variables section
5. Deploy!

The application will be automatically deployed when you push changes to your repository.

## Environment Variables

- `OPENAI_API_KEY`: Your OpenAI API key (required)

## Technology Stack

- Flask (Backend)
- Socket.IO (Real-time communication)
- OpenAI API (GPT-3.5 & Text-to-Speech)
- Web Speech API (Speech recognition)
- Tailwind CSS (Styling) 