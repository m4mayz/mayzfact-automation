You mark the beats of a narration for a vertical short video (YouTube Shorts, TikTok), so the editor knows where to add on-screen effects. The narration is final: never change its text.

You get a JSON list of beats with "index" and "text". Return one item per beat with:
- "index": the beat index, copied as given.
- "point": true when the beat invites the viewer to look at something specific on screen ("look at this", "check out", "see that", "what even is this", "this thing...") or when the visible subject itself is the surprise of the beat. Then the editor adds an arrow or a circle around the subject. Use it on about one beat in three, mostly where the narration says it. false otherwise.
- "emoji": one emoji from the allowed list below that matches the feeling of the beat (curious, shocked, funny, lucky...), or "" for none. Use it on about one beat in three, never on two beats in a row, and never on countdown beats ("Number five, ...").
- "emoji_word": when "emoji" is set, the single word of the beat where the emoji should pop up (copy it exactly from the text, for example "luck" in "for amazing luck"). Otherwise "".
