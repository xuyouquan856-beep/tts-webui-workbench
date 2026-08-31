export function isExampleModel(m: { name: string }): boolean {
  const exampleNames = [
    "Dummy Beep Generator",
    "Local HTTP Model Example",
    "Local Command Execution Example",
    "Piper TTS ONNX Example"
  ];
  return exampleNames.includes(m.name);
}

export function isExampleProfile(p: { name: string }): boolean {
  const exampleNames = [
    "Piper English Voice",
    "Local HTTP Custom Voice"
  ];
  return exampleNames.includes(p.name);
}
