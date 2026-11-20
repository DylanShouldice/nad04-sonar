// Once again the code the client uses when on the post_detail view tpo communicate with the backend in AJAX

console.log("hello world DETAIL.js")

const postBox = document.getElementById('post-box')
const extraBox = document.getElementById('extra-box')
const alertBox = document.getElementById('alert-box')

const backBtn = document.getElementById('back-btn')
const updateBtn = document.getElementById('update-btn')
const deleteBtn = document.getElementById('delete-btn')

const url = window.location.href + "data/"
const updateUrl = window.location.href + "update/"
const deleteUrl = window.location.href + "delete/"

const updateForm = document.getElementById('update-form')
const deleteForm = document.getElementById('delete-form')

const spinnerBox = document.getElementById('spinner-box')

const titleInput = document.getElementById('id_title')
const bodyInput = document.getElementById('id_body')

const csrf = document.getElementsByName('csrfmiddlewaretoken')

// Added alot to this AJAX call, I think it is alot for what I got done but it works so I am happy with it
$.ajax({
    type: 'GET',
    url: url,
    success: function (response) {

        console.log(response);
        const data = response.data;

        if (data.logged_in !== data.author) {
            console.log('different')
        }

        else {
            console.log('the same')
            updateBtn.classList.remove('not-visible')
            deleteBtn.classList.remove('not-visible')
        }
    
        const authorContainer = document.createElement('div');
        authorContainer.setAttribute('class', 'd-flex align-items-center justify-content-between');

        const authorInfo = document.createElement('div');
        authorInfo.setAttribute('class', 'd-flex align-items-center');

        const avatarImg = document.createElement('img');
        avatarImg.setAttribute('src', data.author_avatar);
        avatarImg.setAttribute('class', 'rounded-circle me-2');
        avatarImg.setAttribute('width', '50');
        avatarImg.setAttribute('height', '50');
        avatarImg.setAttribute('alt', `${data.author}'s avatar`);

        const authorName = document.createElement('h6');
        authorName.setAttribute('class', 'mb-0');
        authorName.textContent = data.author;

        authorInfo.appendChild(avatarImg);
        authorInfo.appendChild(authorName);

        const likeContainer = document.createElement('div');
        likeContainer.setAttribute('class', 'd-flex align-items-center');

        const likeButton = document.createElement('button');
        likeButton.setAttribute('class', 'btn btn-sm d-flex align-items-center');
        likeButton.setAttribute('style', 'border: none; background: none; cursor: pointer;');

        const thumbIcon = document.createElement('i');
        thumbIcon.setAttribute('class', `bi bi-hand-thumbs-up${data.liked ? '-fill' : ''}`);
        thumbIcon.setAttribute('style', `font-size: 2rem; color: ${data.liked ? '#007bff' : '#6c757d'};`);

        const likeCount = document.createElement('span');
        likeCount.setAttribute('class', 'ms-2');
        likeCount.textContent = data.count;

        likeButton.appendChild(thumbIcon);
        likeButton.appendChild(likeCount);

        likeButton.addEventListener('click', () => {
            const isLiked = thumbIcon.classList.contains('bi-hand-thumbs-up-fill');
        
            thumbIcon.classList.toggle('bi-hand-thumbs-up');
            thumbIcon.classList.toggle('bi-hand-thumbs-up-fill');
            thumbIcon.style.color = isLiked ? '#6c757d' : '#007bff';
        
            $.ajax({
                type: 'POST',
                url: `${window.location.origin}/${data.id}/like-unlike/`, 
                data: {
                    'csrfmiddlewaretoken': csrf[0].value,
                },
                success: function (response) {
                    console.log('Like updated successfully:', response);
        
                    likeCount.textContent = response.count;
        
                    data.count = response.count;
                },
                error: function (error) {
                    console.log('Error updating like:', error);
        
                    thumbIcon.classList.toggle('bi-hand-thumbs-up');
                    thumbIcon.classList.toggle('bi-hand-thumbs-up-fill');
                    thumbIcon.style.color = isLiked ? '#007bff' : '#6c757d';
                }
            });
        });


        likeContainer.appendChild(likeButton);

        authorContainer.appendChild(authorInfo);
        authorContainer.appendChild(likeContainer);

        extraBox.appendChild(authorContainer);

        titleInput.value = data.title;
        bodyInput.value = data.body;

        const titleElement = document.createElement('h3');
        titleElement.textContent = data.title;
        titleElement.setAttribute('id', 'title')


        const bodyElement = document.createElement('p');
        bodyElement.setAttribute('id', 'body')
        bodyElement.textContent = data.body;

        postBox.appendChild(titleElement);
        postBox.appendChild(bodyElement);

        spinnerBox.classList.add('not-visible');
    },
    error: function (error) {
        console.log(error);
    }
});





updateForm.addEventListener('submit', e => {
    e.preventDefault()

    const title = document.getElementById('title')
    const body = document.getElementById('body')

    $.ajax({
        type: 'POST',
        url: updateUrl,
        data: {
            'csrfmiddlewaretoken': csrf[0].value,
            'title': titleInput.value,
            'body': bodyInput.value,
        },
        success: function (response) {
            console.log(response)
            handleAlerts('success', 'post has been updated')
            title.textContent = response.title
            body.textContent = response.body
        },
        error: function (error) {
            console.log("error", error)
        }
    })
})

deleteForm.addEventListener('submit', e => {
    e.preventDefault()
    console.log('Delete URL:', deleteUrl);
    console.log('CSRF Token:', csrf[0].value);
    $.ajax({
        type: 'POST',
        url: deleteUrl,
        data: {
            'csrfmiddlewaretoken': csrf[0].value,
        },
        success: function (response) {
            console.log(response)
            window.location.href = window.location.origin
            localStorage.setItem('title', titleInput.value)
        },
        error: function (error) {
            console.log("error", error)
        }
    })
})

Dropzone.autoDiscover = false;

const updateDropzone = new Dropzone('#update-dropzone', {
    url: `${window.location.origin}/upload/`, // Adjust the URL to match your backend
    init: function () {
        this.on('sending', function (file, xhr, formData) {
            formData.append('csrfmiddlewaretoken', csrf[0].value);
            formData.append('post_id', document.getElementById('update-post-id').value);
        });
        this.on('success', function (file, response) {
            console.log('File uploaded successfully:', response);
        });
        this.on('error', function (file, error) {
            console.log('Error uploading file:', error);
        });
    },
    maxFiles: 5,
    maxFilesize: 4, // 4 MB
    acceptedFiles: '.png, .jpg, .jpeg',
});