# SensorNetworksDevice

Este repositório contém o firmware para um dispositivo de borda (edge device) baseado na plataforma Pycom LoPy 4, 
desenvolvido para a unidade curricular de Redes de Sensores no Politécnico de Leiria (ESTG). O sistema foi projetado 
para a monitorização contínua de variáveis ambientais, utilizando uma arquitetura de comunicação híbrida que garante 
a resiliência dos dados em cenários de conectividade instável.

# 🛠️ Arquitetura e Tecnologias

- Hardware: Plataforma LoPy 4 (baseada em ESP32) acoplada a uma placa de expansão PySense.

- Linguagem: Implementação modular em MicroPython com arquitetura orientada a serviços.

- Máquina de Estados: O firmware opera sobre uma máquina de estados finita que gere dinamicamente os ciclos de leitura e transmissão.

- Sensores: Aquisição de dados de temperatura, humidade, pressão atmosférica e luminosidade.


# 📡 Estratégia de Comunicação Híbrida

- O dispositivo implementa três interfaces de rede distintas para maximizar a disponibilidade:

- WiFi (MQTT): Interface prioritária ligada ao Broker da Ubidots, utilizando payloads em formato JSON.

- LoRaWAN (Failover): Mecanismo de redundância via The Things Network (TTN). Utiliza ativação OTAA, banda EU868 e transmissão binária otimizada para aumentar o alcance e imunidade ao ruído.

- Bluetooth Low Energy (BLE): Interface de configuração local que permite alterar credenciais WiFi, modos de operação e temporização sem necessidade de reprogramação.


# ✨ Funcionalidades e Otimização

- Failover Automático: Algoritmo de decisão que comuta entre WiFi e LoRaWAN de forma transparente caso a ligação IP falhe.

- Gestão Energética: Utilização de técnicas de Deep Sleep e interrupções de hardware (GPIO Wake-up via pino P14) para estender a autonomia.

- Protocolo de Configuração: Implementação de um protocolo de aplicação leve (TLV - Type-Length-Value) via BLE com fila de confirmação (ACK).

- Visualização Unificada: Integração de fluxos de dados (IP e LPWAN) num dashboard centralizado na plataforma Ubidots.
