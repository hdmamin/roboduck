# Run from ~/roboduck with `make chat_prompt`.
fname="NEW_PROMPT"
read -p "Prompt Name (lowercase, no spaces): " fname
fpath="lib/roboduck/prompts/chat/$fname.yaml"
cp lib/roboduck/prompts/chat/__template__.yaml $fpath
vi $fpath
echo "Prompt saved to $fpath."
