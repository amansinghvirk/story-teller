import os
import logging
import google.generativeai as genai
from langchain_google_genai import GoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field


class Story(BaseModel):
    style: dict = Field(..., title="Style", description="HTML CSS style to be used for the story")
    title: str = Field(..., title="Title", description="Title exctracted for the story")
    introduction: str = Field(..., title="Introduction", description="Introduction for the story")
    story: dict = Field(..., title="Story", description="The story generated by the model")
    theme: dict = Field(..., title="Theme", description="The story theme describing purpose, colors suit to the story")


class StoryGenerator:

    def __init__(self, story_theme: str = "General", story_inspiration: str = "General", n_words: int = 200):
        genai.configure()
        self.language_model = genai.GenerativeModel(os.getenv('LANGUAGE_MODEL'))
        self.image_to_text_model = genai.GenerativeModel(os.getenv('IMAGE_TO_TEXT_MODEL'))
        self.llm = GoogleGenerativeAI(model=os.getenv('LANGUAGE_MODEL'))
        self.story_theme = story_theme
        self.story_inspiration = story_inspiration
        self.n_words = n_words
        self.story_instructions()


    def set_context(self, context: str=None, topic: str=None) -> str:
        self.topic = topic
        self.context = context
        if topic:
            self.topic = topic
            with open("inputs/prompt_w_topic.txt", 'r') as f:
                prompt = f.read()
                self.prompt_template = prompt
                self.input_variables = ["TOPIC", "instructions_placeholder"]

        elif context:
            self.context = context

            self.prompt_template = '''
                Generate a short story based on the context provide in the STORY_CONTEXT section


                INSTRUCTIONS:
                    {instructions_placeholder}

                STORY_CONTEXT:
                {context_placeholder}
            '''

            self.input_variables = ["instructions_placeholder", "context_placeholder"]
            
        else:
            self.prompt_template = "Generate a story on {TOPIC} \nINSTRUCTIONS: \n {instructions_placeholder}"
            self.input_variables = ["TOPIC", "instructions_placeholder"]


    def set_image_context(self, img) -> str:

        self.image = img

        prompt = '''
            **Objective:** Generate a comprehensive and detailed description of the provided image, focusing on aspects that will be useful for subsequent story generation.

            **Instructions:**

            1.  **Image Type & Overall Impression:**
                *   Begin by identifying the image type (e.g., photograph, painting, digital illustration, infographic, chart, etc.).
                *   Provide a brief summary of the overall impression or mood conveyed by the image. Is it whimsical, serious, chaotic, peaceful, etc.?

            2.  **Key Elements and Characters:**
                *   **Identify and Describe:**  Meticulously list and describe all significant elements, objects, and characters present in the image.
                *   **Character Details:** If characters are present, describe their:
                    *   Appearance (age, clothing, facial features, posture, etc.)
                    *   Possible emotions or expressions.
                    *   Interactions with other elements or characters, if any.
                *   **Object Details:** For objects, detail their:
                    *   Shape, size, material, and any distinctive features.
                    *   Position and arrangement within the image.
            
            3. **Visual Style and Aesthetics:**
                *  **Style:** Describe the overall artistic style of the image (e.g., realistic, abstract, cartoonish, impressionistic, etc.).
                * **Color Palette:**  Analyze and specify the dominant colors and color relationships, and describe the overall color scheme. How do they contribute to the image's atmosphere?
                * **Composition:** Comment on how elements are arranged within the image.  Is there a focal point? What are the effects of leading lines, perspectives, and symmetry?
                * **Lighting:** Describe the quality of light in the image (e.g. bright, dim, natural, artificial). How is light used to highlight the characters or create shadows and mood?
                
            4.  **Data and Information (if applicable):**
                *   **Statistical Data:** If the image contains numerical data, statistics, or values, explicitly state the numbers and their meaning. Present this information in a clear and concise manner using bullet points.
                *   **Charts, Graphs, Infographics, Tables:** If the image contains charts, graphs, or tables:
                    *   Describe the type of visualization (e.g., bar chart, pie chart, line graph).
                    *   Identify axes and labels.
                    *   Summarize the key data points and relationships displayed within the visualization.
                *   **Text and Labels:** If there is any text or labels, transcribe and include them in your description as pointers. Explain the purpose of the text.

            5.  **Contextual Relevance:**
                *   **Interpreting the Scene:** Consider if the elements seem related. Is there a sense of space or location?
                *   **Potential Story Hooks:** Briefly note any potential narrative elements that suggest a story. (e.g., a character looking determined, an unusual object, a mysterious atmosphere)

            6.  **Restrictions and Limitations:**
                *   **Image Based:**  Only describe aspects directly visible or inferred from the image.
                *   **Avoid Assumptions:** Do not add information or make assumptions that are not supported by the image content.

            **Example output structure**
            ```
            Type of image: Photograph
            Mood: Serene, nostalgic
            Key Elements:
                - An old wooden rowboat resting on a calm lake.
                - A few tall pine trees surrounding the lake
                - A soft, hazy sunset.

            Characters:
                - No people are present.
                - A family of ducks swimming near the boat.

            Style: Realistic
            Color Palette:
                - Dominant colors are muted shades of blue, grey, green, and orange.
                - The color palette creates a peaceful and somewhat melancholic mood.
            Composition:
                - The composition is horizontally oriented, with the rowboat as a point of interest in the left side, and a lot of empty space on the right

            Data:
            - No data is present
            
            Contextual relevance:
                - Suggests a feeling of peace and tranquility. It could be a scene from the past.

        '''

        self.image_prompt = [prompt, self.image]
        self.context = self.image_to_text_model.generate_content(self.image_prompt).text
        self.prompt_template = '''
            Generate a short story based on the context provide in the STORY_CONTEXT section


            INSTRUCTIONS:
                {instructions_placeholder}

            STORY_CONTEXT:
            {context_placeholder}
        '''
        self.input_variables = ["instructions_placeholder", "context_placeholder"]
    
    def generate_response(self) -> str:
    
        try:

            logging.info("Generating story ...")


            # Set up a parser + inject instructions into the prompt template.
            parser = JsonOutputParser(pydantic_object=Story)
            

            self.prompt = PromptTemplate(
                template=self.prompt_template,
                input_variables=self.input_variables,
                partial_variables={"format_instructions": parser.get_format_instructions()},
            )
            if "context_placeholder" in self.input_variables:
                chain = self.prompt | self.llm | parser

                self.response = chain.invoke(
                    {"instructions_placeholder": self.instrucitons,
                    "context_placeholder": self.context},
                )
            else:
                if self.topic is None:
                    self.topic = "Random"
                
                chain = self.prompt | self.llm | parser
                self.response = chain.invoke(
                    {"instructions_placeholder": self.instrucitons,
                    "TOPIC": self.topic},
                )

            return self.response
        
        except Exception as e:
            raise e
        

    def story_instructions(self):
        self.story_parts = self.n_words // 200
        self.instrucitons = f"""
            You are an expert storyteller and visual content creator. Your task is to generate a compelling and visually engaging story based on provided context. The output should be structured for easy integration into a web application.

            **STORY GENERATION:**

            1.  **Story Length:** The generated story must not exceed a {self.n_words}  word count.
            2.  **Story Segmentation:** Divide the story into a {self.story_parts} number of parts. Each part should flow logically to create a cohesive narrative. 
            3.  **Story Theme:** The story must adhere to a given theme, which will be represented by {self.story_theme}. Ensure the plot, characters, and overall tone align with this theme.
            4.  **Inspiration Source:** Draw inspiration from the provided source, represented by {self.story_inspiration}. This could be a specific event, a historical figure, a literary work, or any other relevant input. Let the inspiration influence the story's narrative, but don't plagiarize directly.
            5.  **Title:** Create a concise and engaging title for the story.
            6.  **Introduction:** Craft a brief introduction (50-60 words) that sets the scene, introduces the main idea, and piques the reader's interest.
            7.  ""Theme:** Create a small description about the theme of the story, this should contain small context, what colors, style will suit to show this story over the web, this will be used to ask a theme generator to generator colors, font-colors, styles for the web page where story will be posted

            **IMAGE PROMPT GENERATION (For Each Story Part):**

            1.  **Purpose:** Generate a distinct, concise, and clear image prompt for each story part. These prompts will be used by a separate image generation model.
            2.  **Context Alignment:** Ensure each image prompt aligns directly with the content of its respective story part.
            3.  **Visual Style:** The generated images should:
                *   Have a light and predominantly white background to accommodate text overlay.
                *   Image and image should match the inspiration from {self.story_inspiration} and theme from {self.story_theme}
                *   Image prompt should clearly mention the color palletes to be used to generate the image, so that following image should have same contrast, colors and backgrounds
            4.  **Prompt Clarity:** The image prompts must be concise, focusing on key visual elements, and avoid unnecessary detail.
            5.  **Prompt Safety:** Prompt should follow the responsible AI guidelines and Do not include anything related to child, sexual orientation, realted to any race, image prompt should be 
                appropriate to the general audience without hurting any sentiments
            6.  **Characters:** If prompt includes to generate any character, person, imaginary figure, then add details of those so that other similar
                prompts of the story parts images should have same characters/persons/imaginary figures in the images.

            **HTML STYLE GUIDE:**

            1.  **Purpose:** Define a cohesive and aesthetically pleasing style guide for the HTML formatting of the story. This will include the background color, font color, and font family.
            2.  **Context Matching:** The style guide must complement the story theme, image styles, and be visually appealing to the target audience. Aim for a smooth, comfortable reading experience that enhances engagement.
            3.  **Specific Attributes:** The style guide will include:
                *   `background-color`: a background color suitable for the story's theme and image aesthetic.
                *   `font-color`: a font color that provides sufficient contrast against the background, ensuring easy readability.
                *   `font-family`:  a readable font family that fits the overall tone and style of the story and image theme.

            **OUTPUT FORMAT (JSON):**

            1.  **Structure:** The output MUST be in JSON format.
            2.  **Top-Level Keys:** The JSON object must contain the following top-level keys: `style`, `title`, `introduction`, and `story`.
                *   `style`: should contain the HTML style parameters which will be passed to HTML component
                    * `background-color`: color to be used as background color for html
                    * `font-color`: color to be used as font color for the story text
                    * `font-family`: which font will be best suited for the story
                *   `title`: The generated title of the story.
                *   `introduction`: The short introduction to the story.
                *   `theme`: The style guide theme for the story to be used for css styling
                *   `story`:  A nested JSON object that contains each story part.
            3.  **Story Parts:** The `story` object will be a nested structure where each key represents a story part number (e.g., `part_1`, `part_2`, etc.).
            4.  **Part Contents:** Each story part (e.g., `part_1`, `part_2`, etc.) will be a nested JSON object with the following keys:
                *   `story`: The generated content of that particular story part.
                *   `image_prompt`: The image prompt for that specific story part.

            **Example JSON structure:**

            ```json
                "style": 
                    "background-color": "#f0f8ff",
                    "font-color": "#333",
                    "font-family": "Arial, sans-serif"
                ,
                "title": "The Magical Treehouse Adventure",
                "introduction": "Lily and Tom discover a hidden treehouse in their backyard, leading them on an amazing adventure through enchanted lands and whimsical creatures.",
                "theme": "Story is of 2 friends about there adventures, styles which will suit for sharing this story will be vibrant, showing high contrast of colors, color pallete which will suit this story might be #A31D1D, #E5D0AC, #FEF9E1"
                "story": 
                    "part_1": 
                        "story": "The sun peeked through the leaves as Lily and Tom stumbled upon a rickety ladder leading to a treehouse hidden among the branches.",
                        "image_prompt": "A sunny, whimsical treehouse hidden in a lush forest with a ladder leading up to it. Light background, 1/3 of a corner should be free for the text."
                    ,
                    "part_2": 
                        "story": "Inside, they found a sparkling map that promised a journey to the land of talking animals.",
                        "image_prompt": "Inside the treehouse, a map glitters invitingly, surrounded by simple wooden furniture, light background, 1/3 corner free for text"
                    ,
                    "part_3": 
                        "story": "They met a friendly fox who gave them directions to the land of happy smiles",
                        "image_prompt": "A smiling fox and two young children standing on a path surrounded by lush green grass, light background, 1/3 corner free for text"
                     
            ```
                    
        """