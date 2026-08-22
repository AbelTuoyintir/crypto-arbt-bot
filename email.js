const nodemailer = require('nodemailer');
require('dotenv').config();

async function sendEmail(subject, text) {
    const transporter = nodemailer.createTransport({
        service: 'gmail',
        auth: {
            user: process.env.EMAIL_USER,
            pass: process.env.EMAIL_PASS
        }
    });

    const mailOptions = {
        from: process.env.EMAIL_USER,
        to: process.env.EMAIL_TO,
        subject: subject,
        text: text
    };

    try {
        await transporter.sendMail(mailOptions);
        console.log('📧 Email sent!');
    } catch (err) {
        console.error('❌ Email failed:', err.message);
    }
}

module.exports = sendEmail;