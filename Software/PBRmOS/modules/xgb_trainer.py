import modules.ai_driver as AIManager

stateWatcher = AIManager.XGB(2, 1024, 12, "StateWatcher")
harvester    = AIManager.XGB(1, 1024, 12, "Harvester")

stateWatcher.train()
harvester.train()

stateWatcher.save_model()
harvester.save_model()