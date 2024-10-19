import { convertToFlexMessage } from 'markdown-flex-message'

const args = process.argv.slice(2);
const markdown = args[0];

if (!markdown) {
    console.error('Please provide markdown input');
    process.exit(1);
}

convertToFlexMessage(markdown)
.then((flexMessage) => {
    console.log(JSON.stringify(flexMessage));
})
.catch((error) => {
    console.error(error);
    process.exit(1);
});

