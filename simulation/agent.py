import numpy as np
import random
from simulation.goal_type import GoalType
import tensorflow as tf

from collections import deque
from tensorflow import keras
from tensorflow.keras.models import load_model


class DQNAgent:
    """A Deep Q-Network agent that learns to choose goals for a critter."""

    def __init__(self, model_file: str, state_size: int, training: bool, verbose: bool):
        self.state_size = state_size
        self.actions = list(GoalType)
        self.action_size = len(GoalType)
        self.verbose = 1 if verbose else 0

        self.memory = deque(maxlen=10000)

        # Hyperparameters
        self.gamma: float = 0.95            # Discount rate for future rewards
        # Initial exploration rate (starts random)
        self.epsilon_min: float = 0.01      # Minimum exploration rate
        # Start from random if we're training.
        self.epsilon: float = 1.0 if training else self.epsilon_min
        self.epsilon_decay: float = 0.99995   # Rate at which to reduce exploration
        self.learning_rate: float = 0.001

        # Update the target network every few ticks
        self.update_target_freq = 100
        self.training_step_counter = 0

        self.model_file = model_file

        self._load()

        self.target_model = self._build_model()
        self._update_target_model()


    def _build_model(self) -> keras.Model:
        """Builds the neural network for the Q-learning model."""
        model = keras.Sequential([
            keras.Input(shape=(self.state_size,)),
            keras.layers.Dense(128, activation='relu'),
            keras.layers.Dense(128, activation='relu'),
            keras.layers.Dense(self.action_size, activation='linear')
        ])
        model.compile(
            loss='mse',
            optimizer=keras.optimizers.Adam(learning_rate=self.learning_rate)
        )
        return model


    def _update_target_model(self):
        """Copies weights from the main model to the target model"""
        self.target_model.set_weights(self.model.get_weights())


    def remember(self, state, goal: GoalType, reward, next_state, died):
        """Stores an experience tuple"""
        self.memory.append((state, self.actions.index(goal), reward,
                            next_state, died))

    def act(self, state) -> GoalType:
        """
        Chooses a Goal based on the current state using an epsilon-greedy
        strategy.
        """
        # Choose a random action based on probability epsilon
        if np.random.rand() <= self.epsilon:
            return self.actions[random.randrange(self.action_size)]

        # Otherwise, ask the model
        act_values = self.model.predict(state, verbose=self.verbose)
        return self.actions[int(np.argmax(act_values[0]))]

    def replay(self, batch_size: int):
        """Trains the neural network with a random batch of past experiences."""
        if len(self.memory) < batch_size:
            return

        minibatch = random.sample(self.memory, batch_size)

        for state, action_index, reward, next_state, done in minibatch:
            target = reward
            if not done:
                # Predict the future reward and add it to the current reward using
                # the target model.
                target = (reward + self.gamma *
                          np.amax(self.target_model.predict(next_state, verbose=0)[0]))

            # Get the model's current prediction for the Q-values of the state
            target_f = self.model.predict(state, verbose=self.verbose)
            # Update the Q-value for the action we took
            target_f[0][action_index] = target

            # Train the model on this one corrected experience
            self.model.fit(state, target_f, epochs=1, verbose=self.verbose)

            self.training_step_counter += 1
            if self.training_step_counter >= self.update_target_freq:
                self._update_target_model()
                self.training_step_counter = 0

        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay

    def save(self):
        """Saves the current model to a file."""
        print(f"Saving model to {self.model_file}")
        self.model.save(self.model_file)

    def _load(self):
        """Loads the model from a file."""
        import os
        if os.path.exists(self.model_file):
            print(f"Loading model from {self.model_file}")
            self.model = load_model(self.model_file)
        else:
            print(
                f"Model file not found at {self.model_file}. Training from scratch.")
            self.model = self._build_model()

        self.model.summary()
