
from services.podcast_summarizer import AzureOpenAISummarizer
import os
from dotenv import load_dotenv
import os


def summarize(transcript: str) -> str:
    client = AzureOpenAISummarizer(
        endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        api_key=os.environ["AZURE_OPENAI_KEY"],
        api_version=os.environ.get("AZURE_OPENAI_API_VERSION"),
        deployment_name=os.environ["AZURE_MODEL_VERSION"]
    )

    return client.summarize_podcast(text=transcript)


if __name__ == "__main__":
    load_dotenv()
    summary = summarize("So let's talk about the optimal way to engage in activities or to consume things that evoke dopamine. How are we supposed to engage with these dopamine evoking activities in ways that are healthy and beneficial for us? How do we achieve these peaks, which are so essential to our well-being and experience of life, without dropping our baseline? And the key lies in intermittent release of dopamine. The real key is to not expect or chase high levels of dopamine release every time we engage in these activities. Now, the smartphone is a very interesting tool for dopamine in light of all this. It's extremely common nowadays to see people texting and doing selfies and communicating in various ways, listening to podcasts, listening to music, doing all sorts of things while they engage in other activities or going to dinner and texting other people or making plans, sharing information. That's all wonderful. It gives depth and richness and color to life. But it isn't just about our distracted nature when we're engaging with the phone. It's also a way of layering in dopamine. And it's no surprise that levels of depression and lack of motivation are really on the increase. There's something called dopamine reward prediction error. When we expect something to happen, we are highly motivated to pursue it. If it happens, great, we get the reward. The reward comes in various chemical forms, including dopamine, and we are more likely to engage in that behavior again. This is the basis of casino gambling. This is how they keep you going back again and again and again, even though on average, the house really does win. Everything that we've talked about until now sets up an explanation or an interpretation of why interacting with digital technology can potentially lead to disruptions or lowering in baseline levels of dopamine. There's a intermittent schedule by which dopamine sometimes arrives, sometimes a little bit, sometimes a lot, sometimes a medium amount. OK, that intermittent reinforcement schedule is actually the best schedule to export to other activities. How do you do that? Well, first of all, if you are engaged in activities, school, sport, relationship, etcetera, where you experience a win, you should be very careful about allowing yourself to experience huge Eaks in dopamine, unless you're willing to suffer the the crash that follows and waiting a period of time for it to come back. ")
    print(summary)
