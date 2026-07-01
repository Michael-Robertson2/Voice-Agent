from openai import OpenAI
import os


async def bug_logger(timestamp):
    # Only analyze the transcript if the file was created by the bot.
    if os.path.exists(f"transcripts/transcript_{timestamp}.txt"):
        print("Transcript file exists. Sending to OpenAI API for processing...")
        if not os.path.exists("bug_reports"):
            os.makedirs("bug_reports")
        
        client = OpenAI()

        # Upload the transcript so the model can review it as input.
        file = client.files.create(
            file=open(f"transcripts/transcript_{timestamp}.txt", "rb"),
            purpose="user_data"
        )

        response = client.responses.create(
            model="gpt-5.5",
            input= [
                {
                    "role": "system",
                    "content": '''You will be given a transcript of a conversation between two AI agents.
                                One of them is acting as a receptionist for a medical facility, and the other is acting as a patient calling the facility while trying to test the receptionist's system.
                                Analyze the transcript and provide a summary of any bugs, issues, or areas for improvement that you find in the receptionist's system. 
                                Format the report cleanly with clear headings and bullet points for each issue. Include any suggestions for how to fix the issues you identify.'''
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_file",
                            "file_id": file.id,
                        }
                    ]
                }
            ]
        )

        # Save the generated issue summary for later inspection.
        summary = response.output_text
        with open(f"bug_reports/summary_{timestamp}.txt", "w") as summary_file:
            summary_file.write(summary)

        
    else:
        print(f"Transcript file transcripts/transcript_{timestamp}.txt does not exist.")