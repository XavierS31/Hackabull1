Project System Architecture
1. Data Inputs (Hardware)

The system receives input data from wearable hardware:
Glasses

    Camera: Video feed sent to the backend.

    Buzzing Screen: Haptic and visual feedback received from the backend.

Glove

    Camera: Additional visual data sent to the backend.

    MPU (Motion Processing Unit): Motion data sent to the backend.

    IR (Infrared Sensor): Environmental data sent to the backend.

2. Agentic Backend

This is the central processing unit that receives raw data and manages data processing.

    Process JSON Data: Raw data is converted into a structured JSON format.

    QR: Data is routed via QR protocols.

3. Specialized Agents

Structured data is processed by multiple specialized agents that communicate in a feedback loop.
Chatbot

    Receives data.

    Asks clarification questions.

    Sends data to other agents.

Falling Agent

    Reads camera feed.

    Reads MPU data.

    Logic: if data = falls, then:

        Call 911 & family.

        Record the event.

Conversation Agent

    Sees camera feed.

    Enables communication: "you talk about what you see."

Vision Agent

    Tells up surroundings.

    Helps user to walk.

    Logic: uses IR → alerts.

Tracking Dementia

    Tracks what happens.

    Saves event logs.

    Enables the ability to "ask about this" (historical data retrieval).

4. Triggers & Microcontrol

The system is managed by specific inputs and hardware controls.
Triggers

Events are initiated by:

    MPU sensor

    IR sensor

    Surroundings

    TRACK (manual input)

    TALK (manual input)

Microcontrol

Low-level operations include:

    I/U + IR Microcontrol (Interface Unit and Infrared processing)

    ac voice (Voice activity control)