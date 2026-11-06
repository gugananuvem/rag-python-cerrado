const path = require('path');
const { AWSLocalSimulator } = require('@gugananuvem/aws-local-simulator');

// Caminhos do config (ex.: codePath: "src") e dos dados são relativos ao cwd.
// Fixa o cwd na pasta backend para funcionar de qualquer diretório.
process.chdir(__dirname);

// Arquivo de configuração (serviços, portas, tabelas DynamoDB, lambdas, etc.).
// Padrão: aws-local-simulator.json (Lambda Python por processo, sem runtime server).
// Debug:  node server.js aws-local-simulator.debug.json (ver `npm run start:debug`).
const configPath = path.resolve(__dirname, process.argv[2] || 'aws-local-simulator.json');
console.log(`Config: ${configPath}`);

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
