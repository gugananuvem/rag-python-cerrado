const path = require('path');
const { AWSLocalSimulator } = require('@gugananuvem/aws-local-simulator');

// Aponta para o arquivo de configuração local (serviços, portas, tabelas DynamoDB, etc.)
const configPath = path.join(__dirname, 'aws-local-simulator.json');

const simulator = new AWSLocalSimulator({ configPath });

async function main() {
  await simulator.start();

  const status = simulator.getStatus();
  console.log('Serviços ativos:', JSON.stringify(status.services, null, 2));
  console.log('AWS Local Simulator rodando. Pressione Ctrl+C para parar.');
}

// Encerramento gracioso
async function shutdown(signal) {
  console.log(`\nRecebido ${signal}, parando o simulador...`);
  try {
    await simulator.stop();
  } catch (err) {
    console.error('Erro ao parar o simulador:', err);
  } finally {
    process.exit(0);
  }
}

process.on('SIGINT', () => shutdown('SIGINT'));
process.on('SIGTERM', () => shutdown('SIGTERM'));

main().catch((err) => {
  console.error('Falha ao iniciar o AWS Local Simulator:', err);
  process.exit(1);
});
