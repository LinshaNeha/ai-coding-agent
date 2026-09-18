const vscode = require('vscode');
const https = require('https');
const http = require('http');

function activate(context) {
  console.log('AI Coding Agent extension activated');

  const askQuestionCommand = vscode.commands.registerCommand(
    'aiCodingAgent.askQuestion',
    async () => {
      const config = vscode.workspace.getConfiguration('aiCodingAgent');
      const apiUrl = config.get('apiUrl');
      const apiKey = config.get('apiKey');

      if (!apiUrl || !apiKey) {
        vscode.window.showErrorMessage(
          'AI Coding Agent: Please set apiUrl and apiKey in Settings first.'
        );
        return;
      }

      const question = await vscode.window.showInputBox({
        prompt: 'Ask a question about your codebase',
        placeHolder: 'e.g. How does the retriever work?'
      });

      if (!question) return;

      vscode.window.withProgress(
        { location: vscode.ProgressLocation.Notification, title: 'Asking AI Coding Agent...' },
        async () => {
          try {
            const result = await callChatApi(apiUrl, apiKey, question);
            showAnswerPanel(question, result);
          } catch (err) {
            vscode.window.showErrorMessage('AI Coding Agent error: ' + err.message);
          }
        }
      );
    }
  );

  const fixFileCommand = vscode.commands.registerCommand(
    'aiCodingAgent.fixCurrentFile',
    async () => {
      const editor = vscode.window.activeTextEditor;
      if (!editor) {
        vscode.window.showErrorMessage('No file is open.');
        return;
      }

      const config = vscode.workspace.getConfiguration('aiCodingAgent');
      const apiUrl = config.get('apiUrl');
      const apiKey = config.get('apiKey');

      if (!apiUrl || !apiKey) {
        vscode.window.showErrorMessage(
          'AI Coding Agent: Please set apiUrl and apiKey in Settings first.'
        );
        return;
      }

      const filePath = vscode.workspace.asRelativePath(editor.document.uri);
      const testPath = await vscode.window.showInputBox({
        prompt: 'Path to tests to verify the fix against',
        value: 'tests'
      });

      if (!testPath) return;

      vscode.window.withProgress(
        { location: vscode.ProgressLocation.Notification, title: 'Running fix-loop...' },
        async () => {
          try {
            const result = await callFixApi(apiUrl, apiKey, filePath, testPath);
            if (result.changed) {
              await vscode.workspace.fs.stat(editor.document.uri);
              const doc = await vscode.workspace.openTextDocument(editor.document.uri);
              await vscode.window.showTextDocument(doc);
              vscode.window.showInformationMessage(
                result.success
                  ? `Fix applied and tests passing (${result.attempts} attempt(s)).`
                  : `Fix applied but tests still failing after ${result.attempts} attempt(s). Check the file.`
              );
            } else {
              vscode.window.showInformationMessage('No changes were needed -- tests already pass.');
            }
          } catch (err) {
            vscode.window.showErrorMessage('AI Coding Agent error: ' + err.message);
          }
        }
      );
    }
  );

  context.subscriptions.push(askQuestionCommand, fixFileCommand);
}

function callChatApi(apiUrl, apiKey, question) {
  return callApi(apiUrl, '/chat', apiKey, { question });
}

function callFixApi(apiUrl, apiKey, filePath, testPath) {
  return callApi(apiUrl, '/agent/fix', apiKey, { file_path: filePath, test_path: testPath });
}

function callApi(baseUrl, path, apiKey, body) {
  return new Promise((resolve, reject) => {
    const url = new URL(path, baseUrl);
    const client = url.protocol === 'https:' ? https : http;
    const data = JSON.stringify(body);

    const req = client.request(
      url,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': apiKey,
          'Content-Length': Buffer.byteLength(data)
        }
      },
      (res) => {
        let raw = '';
        res.on('data', (chunk) => (raw += chunk));
        res.on('end', () => {
          try {
            const parsed = JSON.parse(raw);
            if (res.statusCode >= 400) {
              reject(new Error(parsed.detail ? JSON.stringify(parsed.detail) : `HTTP ${res.statusCode}`));
            } else {
              resolve(parsed);
            }
          } catch (e) {
            reject(new Error('Invalid response from server'));
          }
        });
      }
    );

    req.on('error', reject);
    req.write(data);
    req.end();
  });
}

function showAnswerPanel(question, result) {
  const panel = vscode.window.createWebviewPanel(
    'aiCodingAgentAnswer',
    'AI Coding Agent: Answer',
    vscode.ViewColumn.Beside,
    {}
  );

  const sourcesHtml = (result.sources || [])
    .map(
      (s) =>
        `<div style="margin-bottom:6px;font-size:12px;opacity:0.7;">${s.chunk_name} (${s.file_path}) -- similarity ${s.similarity.toFixed(2)}</div>`
    )
    .join('');

  panel.webview.html = `
    <html>
      <body style="font-family: sans-serif; padding: 16px; line-height: 1.5;">
        <h3>Q: ${escapeHtml(question)}</h3>
        <p>${escapeHtml(result.answer).replace(/\n/g, '<br>')}</p>
        <hr>
        <div>${sourcesHtml}</div>
        <div style="margin-top:10px; opacity:0.6; font-size:12px;">
          ${result.tier || ''} ${result.model_used ? '· ' + result.model_used : ''} ${result.latency_ms ? '· ' + result.latency_ms + 'ms' : ''}
          ${result.cached ? '· cached' : ''}
        </div>
      </body>
    </html>
  `;
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

function deactivate() {}

module.exports = { activate, deactivate };